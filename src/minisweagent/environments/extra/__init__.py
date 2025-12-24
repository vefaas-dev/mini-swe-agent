from .vefaas.utils import check_env
from .vefaas.apig import get_function_endpoint

# Initialize global variables for VEFAAS
_env_config = check_env()
VEFAAS_ACCESS_KEY = _env_config["access_key"]
VEFAAS_SECRET_KEY = _env_config["secret_key"]
VEFAAS_FUNCTION_ID = _env_config["function_id"]
VEFAAS_REGION = _env_config["region"]
VEFAAS_APIG_ENDPOINT = get_function_endpoint(
    VEFAAS_ACCESS_KEY,
    VEFAAS_SECRET_KEY,
    VEFAAS_REGION,
    VEFAAS_FUNCTION_ID
)
