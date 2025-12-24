
import threading
from pathlib import PurePath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from swerex.deployment.abstract import AbstractDeployment


class LocalDeploymentConfig(BaseModel):
    """Configuration for running locally."""

    type: Literal["local"] = "local"
    """Discriminator for (de)serialization/CLI. Do not change."""

    model_config = ConfigDict(extra="forbid")

    def get_deployment(self) -> AbstractDeployment:
        from swerex.deployment.local import LocalDeployment

        return LocalDeployment.from_config(self)


class RemoteDeploymentConfig(BaseModel):
    """Configuration for `RemoteDeployment`, a wrapper around `RemoteRuntime` that can be used to connect to any
    swerex server.
    """

    auth_token: str
    """The token to use for authentication."""
    host: str = "http://127.0.0.1"
    """The host to connect to."""
    port: int | None = None
    """The port to connect to."""
    timeout: float = 0.15

    type: Literal["remote"] = "remote"
    """Discriminator for (de)serialization/CLI. Do not change."""

    model_config = ConfigDict(extra="forbid")

    def get_deployment(self) -> AbstractDeployment:
        from swerex.deployment.remote import RemoteDeployment

        return RemoteDeployment.from_config(self)


class VefaasDeploymentConfig(BaseModel):
    """Configuration for VEFAAS deployment."""

    image: str | None = None
    """Docker image to use for the sandbox. If not provided, uses random from image_list_file."""
    command: str = "curl -fsSL https://vefaas-swe.tos-cn-beijing.ivolces.com/swe-rex/install_1.4.0.sh | bash -s -- {token}"
    """Command to run in the sandbox with authentication token."""
    timeout: float = 60.0
    """  timeout for sandbox live """
    startup_timeout: float = 120.0
    """Timeout waiting for runtime to start."""
    function_id: str | None = None
    """VEFAAS function ID."""
    access_key: str | None = None
    """VEFAAS access key."""
    secret_key: str | None = None
    """VEFAAS secret key."""
    region: str = "cn-beijing"
    apig_endpoint: str | None = None
    port: int = 8000
    sandbox_envs: dict[str, str] = Field(default_factory=dict)

    type: Literal["vefaas"] = "vefaas"
    """Discriminator for (de)serialization/CLI. Do not change."""

    model_config = ConfigDict(extra="forbid")

    def get_deployment(self) -> AbstractDeployment:
        from minisweagent.environments.extra.vefaas.vefaas import VefaasDeployment

        return VefaasDeployment.from_config(self)


DeploymentConfig = (
        LocalDeploymentConfig
        | RemoteDeploymentConfig
        | VefaasDeploymentConfig
)
"""Union of all deployment configurations. Useful for type hints."""


def get_deployment(
        config: DeploymentConfig,
) -> AbstractDeployment:
    return config.get_deployment()
