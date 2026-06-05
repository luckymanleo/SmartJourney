"""
阿里云号码认证服务 — Dypnsapi SendSmsVerifyCode / CheckSmsVerifyCode

短信验证码由阿里云系统自动生成（##code## 占位符），验证码校验通过
CheckSmsVerifyCode API。OutId 用于关联发送和校验。
"""

import json
import logging
from uuid import uuid4

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import (
    ClientException,
    ServerException,
)
from aliyunsdkdypnsapi.request.v20170525.SendSmsVerifyCodeRequest import (
    SendSmsVerifyCodeRequest,
)
from aliyunsdkdypnsapi.request.v20170525.CheckSmsVerifyCodeRequest import (
    CheckSmsVerifyCodeRequest,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_client() -> AcsClient:
    """创建阿里云 ACS 客户端"""
    return AcsClient(
        settings.sms_access_key_id,
        settings.sms_access_key_secret,
        settings.sms_region,
    )


async def send_verify_code(phone: str) -> tuple[bool, str, str | None]:
    """发送短信验证码（由阿里云系统自动生成验证码）

    Args:
        phone: 手机号（11 位大陆手机号）

    Returns:
        (success, message, out_id)
        out_id: 外部流水号，用于后续 CheckSmsVerifyCode 校验；
                失败时为 None
    """
    client = _build_client()
    request = SendSmsVerifyCodeRequest()

    out_id = str(uuid4())

    request.set_SignName(settings.sms_sign_name)
    request.set_TemplateCode(settings.sms_template_code)
    request.set_PhoneNumber(phone)
    # ##code## 占位符：系统自动生成验证码并替换
    request.set_TemplateParam(json.dumps({"code": "##code##", "min": "5"}))
    request.set_OutId(out_id)

    try:
        response = client.do_action_with_exception(request)
        result = json.loads(response)

        if result.get("Code") == "OK":
            logger.info(f"[SMS] 验证码已发送到 {phone} (OutId={out_id})")
            return True, "验证码已发送", out_id
        else:
            error_msg = result.get("Message", "未知错误")
            logger.error(
                f"[SMS] 发送失败 {phone}: "
                f"Code={result.get('Code')} Message={error_msg}"
            )
            return False, f"短信发送失败: {error_msg}", None

    except ServerException as e:
        logger.error(f"[SMS] 服务器异常 {phone}: {e.error_code} - {e.message}")
        return False, f"短信服务异常: {e.message}", None
    except ClientException as e:
        logger.error(f"[SMS] 客户端异常 {phone}: {e.error_code} - {e.message}")
        return False, f"短信配置错误: {e.message}", None
    except Exception as e:
        logger.error(f"[SMS] 未知异常 {phone}: {e}")
        return False, "短信发送失败，请稍后重试", None


async def check_verify_code(phone: str, code: str, out_id: str) -> tuple[bool, str]:
    """校验短信验证码（调用阿里云 CheckSmsVerifyCode）

    Args:
        phone: 手机号
        code: 用户输入的验证码
        out_id: send_verify_code 返回的外部流水号

    Returns:
        (valid, message)
    """
    client = _build_client()
    request = CheckSmsVerifyCodeRequest()

    request.set_PhoneNumber(phone)
    request.set_VerifyCode(code)
    request.set_OutId(out_id)

    try:
        response = client.do_action_with_exception(request)
        result = json.loads(response)

        if result.get("Code") == "OK":
            verify_result = result.get("Model", {}).get("VerifyResult", "")
            if verify_result == "PASS":
                logger.info(f"[SMS] 验证码校验通过 {phone}")
                return True, "验证通过"
            else:
                logger.warning(f"[SMS] 验证码错误 {phone}: {verify_result}")
                return False, "验证码错误"
        else:
            error_msg = result.get("Message", "未知错误")
            logger.warning(f"[SMS] 校验失败 {phone}: {error_msg}")
            return False, "验证码错误"

    except ServerException as e:
        logger.error(f"[SMS] 校验服务器异常 {phone}: {e.error_code} - {e.message}")
        return False, "验证服务异常，请重试"
    except ClientException as e:
        logger.error(f"[SMS] 校验客户端异常 {phone}: {e.error_code} - {e.message}")
        return False, "验证服务异常，请重试"
    except Exception as e:
        logger.error(f"[SMS] 校验未知异常 {phone}: {e}")
        return False, "验证失败，请稍后重试"
