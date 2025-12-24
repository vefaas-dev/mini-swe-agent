import time,os
from collections.abc import Callable
import volcenginesdkcore



def get_sdk_configuration(access_key: str, secret_key: str, region: str) -> volcenginesdkcore.Configuration:
    configuration = volcenginesdkcore.Configuration()
    configuration.ak = access_key
    configuration.sk = secret_key
    configuration.read_timeout = 40
    configuration.connect_timeout = 40
    configuration.auto_retry = False
    configuration.region = region
    configuration.client_side_validation = True
    return configuration

os.environ["VOLC_REGION"] = "cn-beijing"

async def wait_until_alive(
        function: Callable, timeout: float = 10.0, function_timeout: float | None = 0.1, sleep: float = 0.25
):
    """Wait until the function returns a truthy value.

    Args:
        function: The function to wait for.
        timeout: The maximum time to wait.
        function_timeout: The timeout passed to the function.
        sleep: The time to sleep between attempts.

    Raises:
        TimeoutError
    """
    end_time = time.time() + timeout
    n_attempts = 0
    await_response = None
    while time.time() < end_time:
        await_response = await function(timeout=function_timeout)
        if await_response:
            return
        time.sleep(sleep)
        n_attempts += 1
    last_response_message = await_response.message if await_response else None
    msg = (
        f"Runtime did not start within {timeout}s (tried to connect {n_attempts} times). "
        f"The last await response was:\n{last_response_message}"
    )
    raise TimeoutError(msg)

def check_env():
    access_key = os.getenv("VEFAAS_ACCESS_KEY") or os.getenv("VOLC_ACCESSKEY")
    secret_key = os.getenv("VEFAAS_SECRET_KEY") or os.getenv("VOLC_SECRETKEY")
    function_id = os.getenv("VEFAAS_FUNCTION_ID") or os.getenv("_FAAS_FUNC_ID")
    region = os.getenv("VOLC_REGION") or "cn-beijing"

    missing = []
    if not access_key: missing.append("ACCESS_KEY")
    if not secret_key: missing.append("SECRET_KEY")
    if not function_id: missing.append("VEFAAS_FUNCTION_ID")

    if missing:
        raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

    return ({
        "access_key": access_key,
        "secret_key": secret_key,
        "function_id": function_id,
        "region": region
    })