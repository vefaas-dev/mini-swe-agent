import asyncio
import os
from typing import Any

from pydantic import BaseModel, ConfigDict
from minisweagent.environments.extra.vefaas.vefaas import VefaasDeployment
from minisweagent.environments.extra.vefaas.config import VefaasDeploymentConfig
from . import (
    VEFAAS_ACCESS_KEY,
    VEFAAS_SECRET_KEY,
    VEFAAS_FUNCTION_ID,
    VEFAAS_REGION,
    VEFAAS_APIG_ENDPOINT,
)
from minisweagent.utils.log import logger
from swerex.runtime.abstract import Command as RexCommand


class SwerexVefaasEnvironmentConfig(BaseModel):
    image: str | None = None
    cwd: str = "/"
    """Working directory in which to execute commands."""
    deployment_extra_kwargs: dict[str, Any] = {}
    """Extra kwargs to pass to VefaasDeployment."""
    model_config = ConfigDict(extra="allow")

    execute_timeout: float = 60.0
    """Timeout for command execution."""


class SwerexVefaasEnvironment:
    def __init__(self, **kwargs):
        """This class executes bash commands in a VEFAAS sandbox using SWE-ReX for sandboxing."""
        self.config = SwerexVefaasEnvironmentConfig(**kwargs)

        vd_config = VefaasDeploymentConfig(**{k: v for k, v in self.config.model_dump().items() if k in VefaasDeploymentConfig.model_fields})
        vd_config.access_key = VEFAAS_ACCESS_KEY
        vd_config.secret_key = VEFAAS_SECRET_KEY
        vd_config.function_id = VEFAAS_FUNCTION_ID
        vd_config.region = VEFAAS_REGION
        vd_config.apig_endpoint = VEFAAS_APIG_ENDPOINT

        deployment_kwargs = vd_config.model_dump()
        deployment_kwargs.update(self.config.deployment_extra_kwargs)
        self.deployment = VefaasDeployment(logger=logger, **deployment_kwargs)
        asyncio.run(self.deployment.start())

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the environment and return the raw output."""
        output = asyncio.run(
            self.deployment.runtime.execute(
                RexCommand(
                    command=command,
                    shell=True,
                    check=False,
                    cwd=cwd or self.config.cwd,
                    timeout=timeout or self.config.execute_timeout,
                    merge_output_streams=True,
                )
            )
        )
        return {
            "output": output.stdout,
            "returncode": output.exit_code,
        }

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump()

    def cleanup(self):
        asyncio.run(self.deployment.stop())

    def __del__(self):
        self.cleanup()

