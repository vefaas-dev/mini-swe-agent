import volcenginesdkvefaas
import volcenginesdkcore
import volcenginesdkapig20221112 as apig
import json
from typing import Optional
from minisweagent.environments.extra.vefaas.utils import get_sdk_configuration


def get_apig_client(
        access_key: str, secret_key: str, region: str
) -> apig.APIG20221112Api:
    configuration = get_sdk_configuration(access_key, secret_key, region)
    api_client = volcenginesdkcore.ApiClient(configuration)
    return apig.APIG20221112Api(api_client)


def get_vefaas_client(
        access_key: str, secret_key: str, region: str
) -> volcenginesdkvefaas.VEFAASApi:
    configuration = get_sdk_configuration(access_key, secret_key, region)
    api_client = volcenginesdkcore.ApiClient(configuration)
    return volcenginesdkvefaas.VEFAASApi(api_client)



def list_triggers(client: volcenginesdkvefaas.VEFAASApi, function_id: str) -> volcenginesdkvefaas.ListTriggersResponse:
    """获取函数的所有触发器"""
    list_req = volcenginesdkvefaas.ListTriggersRequest(function_id=function_id)
    return client.list_triggers(list_req)


def get_apig_trigger(client: volcenginesdkvefaas.VEFAASApi, function_id: str) -> Optional[volcenginesdkvefaas.ItemForListTriggersOutput]:
    """获取函数的 APIG 类型触发器"""
    triggers = list_triggers(client, function_id)
    for trigger in triggers.items:
        if trigger.type == "apig":
            return trigger
    return None


def list_routes(client: apig.APIG20221112Api, upstream_id: str) -> apig.ListRoutesResponse:
    """获取指定 upstream 的所有路由"""
    list_req = apig.ListRoutesRequest(upstream_id=upstream_id)
    return client.list_routes(list_req)

def get_route_domains_by_id(client: apig.APIG20221112Api, upstream_id: str) -> list[apig.DomainForListRoutesOutput]:
    """获取指定路由 ID 的路由详情"""
    routes  = list_routes(client, upstream_id)
    for route in routes.items:
        return route.domains
    raise ValueError(f"Route {upstream_id} not found")



def parse_upstream_id(detailed_config: str) -> Optional[str]:
    """
    从 DetailedConfig JSON 字符串中解析 UpstreamId

    Args:
        detailed_config: JSON 格式字符串，例如 '{"UpstreamId":"xxx","GatewayId":"yyy"}'

    Returns:
        UpstreamId 字符串，解析失败返回 None

    Raises:
        json.JSONDecodeError: 当 JSON 格式无效时抛出
    """
    try:
        config = json.loads(detailed_config)
        return config.get("UpstreamId")
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Failed to parse UpstreamId from detailed_config: {detailed_config}") from e



def get_function_endpoint(access_key: str, secret_key: str, region: str, function_id: str) -> str:
    """
    获取函数的公网 HTTPS 端点

    Args:
        access_key: VEFaaS 访问密钥
        secret_key: VEFaaS 密钥
        region: VEFaaS 区域
        function_id: 函数 ID

    Returns:
        函数的公网 HTTPS 端点 URL

    Raises:
        ValueError: 当无法获取端点时抛出，包含详细错误信息
    """
    # 获取 APIG 触发器
    vefaas_client = get_vefaas_client(access_key, secret_key, region)
    apig_client = get_apig_client(access_key, secret_key, region)
    trigger = get_apig_trigger(vefaas_client, function_id)
    if trigger is None:
        raise ValueError(f"Function {function_id} has no APIG trigger")

    # 从 detailed_config 字符串中解析 UpstreamId
    upstream_id = parse_upstream_id(trigger.detailed_config)
    if not upstream_id:
        raise ValueError(f"Failed to parse UpstreamId from detailed_config: {trigger.detailed_config}")

    # 获取路由的所有域名
    domains = get_route_domains_by_id(apig_client, upstream_id)

    # 查找公网 HTTPS 域名
    for domain_obj in domains:
       if domain_obj.type == 'public' and domain_obj.domain and domain_obj.domain.startswith('https://'):
            print(f"Found function apig public domain: {domain_obj.domain}")
            return domain_obj.domain

    # 所有路由都没有公网 HTTPS 域名
    raise ValueError(f"No public HTTPS domain found for any routes under upstream {upstream_id}")