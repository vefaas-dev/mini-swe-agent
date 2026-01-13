import logging
import os
import shlex
import subprocess
import uuid
from swerex.deployment.abstract import AbstractDeployment
from swerex.deployment.hooks.abstract import DeploymentHook
from swerex.runtime.abstract import IsAliveResponse
from minisweagent.environments.extra.vefaas.config import VefaasDeploymentConfig
from minisweagent.environments.extra.vefaas.remote import *
from minisweagent.environments.extra.vefaas.utils import wait_until_alive,check_env,get_sdk_configuration
from minisweagent.environments.extra.vefaas.apig import get_apig_client,get_function_endpoint,get_vefaas_client
import volcenginesdkcore
import volcenginesdkvefaas
from volcenginesdkcore.rest import ApiException
from typing import Any
from typing_extensions import Self
import asyncio
import time


def create_sandbox(
        client: volcenginesdkvefaas.VEFAASApi,
        config: VefaasDeploymentConfig,
        logger: logging.Logger,
) -> str | None:
    global image
    if config.image.startswith("docker.io/swebench/"):
        # 去除命名空间并添加域名前缀
        image_name = config.image.replace("docker.io/swebench/", "", 1)
        image = f"enterprise-public-cn-beijing.cr.volces.com/swe-bench/{image_name}"
    else:
        image = config.image
    instance_image_info = (
        volcenginesdkvefaas.InstanceImageInfoForCreateSandboxInput(
                image=image,
                port=config.port,  # swerex server port
                command=config.command,
            )
        )
    start_time = time.time()
    try:
        resp = client.create_sandbox(
            volcenginesdkvefaas.CreateSandboxRequest(
                function_id=config.function_id,
                cpu_milli=2000,
                memory_mb=4096,
                instance_image_info=instance_image_info,
                timeout=int(config.timeout),
                envs=[
                    volcenginesdkvefaas.EnvForCreateSandboxInput(
                        key=name,
                        value=value,
                    )
                    for name, value in config.sandbox_envs.items()
                ]
            )
        )
        end_time = time.time()
        logger.info(
            f"Sandbox {resp.sandbox_id} created in {end_time - start_time:.2f}s"
        )
        return resp.sandbox_id
    except Exception as e:
        end_time = time.time()
        logger.error(
            f"Sandbox creation for {image} failed in {end_time - start_time:.2f}s: {e}"
        )
        return None

def delete_sandbox(
        client: volcenginesdkvefaas.VEFAASApi,
        function_id: str,
        sandbox_id: str,
        logger: logging.Logger,
):
    if sandbox_id is None:
        return
    try:
        client.kill_sandbox(
            volcenginesdkvefaas.KillSandboxRequest(
                function_id=function_id,
                sandbox_id=sandbox_id,
            )
        )
    except ApiException as e:
        logger.error(f"Exception when deleting sandbox {sandbox_id}: {e}")



class VefaasDeployment(AbstractDeployment):
    def __init__(self, *args, logger: logging.Logger | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._config = VefaasDeploymentConfig(**kwargs)

        if "command" not in kwargs:
            env_command = os.getenv("VEFAAS_COMMAND")
            if env_command:
                self._config.command = env_command

        self._runtime: RemoteRuntime | None = None
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self._sandbox_id: str | None = None
        self._stopped: bool = False
        self._hooks = DeploymentHook()

        self.client = get_vefaas_client(self._config.access_key, self._config.secret_key, self._config.region)

    def add_hook(self, hook: DeploymentHook):
        pass

    @classmethod
    def from_config(cls, config: VefaasDeploymentConfig) -> Self:
        return cls(**config.model_dump())

    async def is_alive(self, *, timeout: float | None = None) -> IsAliveResponse:
        if self._runtime is None:
            raise Exception("Runtime not started")
        return await self._runtime.is_alive(timeout=timeout)

    async def _wait_until_alive(self, timeout: float = 10.0):
        try:
            return await wait_until_alive(
                self.is_alive, timeout=timeout, function_timeout=10
            )
        except TimeoutError as e:
            self.logger.error("Runtime did not start within timeout.")
            await self.stop()
            raise e

    def _get_token(self) -> str:
        return str(uuid.uuid4())

    async def start(self):
        self.logger.info("Starting vefaas deployment")
        function_id = self._config.function_id
        if not function_id:
            raise ValueError("VEFAAS_FUNCTION_ID environment variable or function_id in config not set")

        image = self._config.image

        if not image:
            raise ValueError("No image specified and no image list provided")

        token = self._get_token()
        command = self._config.command.format(token=token)
        self._config.command = command

        self.logger.info(f"Creating sandbox with image {image}")
        self._hooks.on_custom_step("Creating vefaas sandbox")
        loop = asyncio.get_running_loop()
        self._sandbox_id = await loop.run_in_executor(
            None,
            create_sandbox,
            self.client,
            self._config,
            self.logger,
        )

        if not self._sandbox_id:
            raise RuntimeError("Failed to create sandbox")

        self._hooks.on_custom_step("Starting runtime")

        function_route = self._config.apig_endpoint
        runtime_config = RemoteRuntimeConfig(
            base_url=function_route,
            extra_params={"faasInstanceName": self._sandbox_id},
            auth_token=token,
            timeout=self._config.timeout,
        )
        self._runtime = RemoteRuntime.from_config(runtime_config)

        await self._wait_until_alive(timeout=120)
        self.logger.info("Runtime started")

    async def stop(self):
        # Prevent duplicate stops
        if getattr(self, '_stopped', False):
            return

        if self._runtime:
            await self._runtime.close()
            self._runtime = None

        if self._sandbox_id:
            self.logger.info(f"Deleting sandbox {self._sandbox_id}")
            function_id = self._config.function_id
            if not function_id:
                self.logger.error(
                    "VEFAAS_FUNCTION_ID or function_id in config not set, cannot delete sandbox"
                )
                return

            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    delete_sandbox,
                    self.client,
                    function_id,
                    self._sandbox_id,
                    self.logger,
                )
                self.logger.info(f"Sandbox {self._sandbox_id} deleted")
            except Exception as e:
                self.logger.error(f"Failed to delete sandbox {self._sandbox_id}: {e}")
            finally:
                self._sandbox_id = None

        self._stopped = True

    @property
    def runtime(self) -> RemoteRuntime:
        if self._runtime is None:
            raise Exception("Runtime not started")
        return self._runtime

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    def __del__(self):
        if hasattr(self, '_sandbox_id') and self._sandbox_id and not getattr(self, '_stopped', False):
            msg = "Ensuring vefaas deployment is stopped because object is deleted"
            try:
                self.logger.debug(msg)
            except Exception:
                print(msg)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.stop())
                else:
                    loop.run_until_complete(self.stop())
            except Exception:
                pass
        # Mark as stopped to prevent duplicate cleanup
        self._stopped = True
