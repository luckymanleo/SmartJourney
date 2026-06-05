"""
阿里云 Dypnsapi 短信验证码测试脚本

用法:
    cd backend && source .venv/bin/activate

    # 发送验证码
    python scripts/test_sms.py send 15280766578

    # 校验验证码（需要先发送拿到 OutId）
    python scripts/test_sms.py check 15280766578 123456 <out_id>

    # 完整流程（发送 + 交互式校验）
    python scripts/test_sms.py 15280766578
"""

import asyncio
import json
import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from aliyunsdkcore.client import AcsClient
from aliyunsdkdypnsapi.request.v20170525.SendSmsVerifyCodeRequest import (
    SendSmsVerifyCodeRequest,
)
from aliyunsdkdypnsapi.request.v20170525.CheckSmsVerifyCodeRequest import (
    CheckSmsVerifyCodeRequest,
)


def get_config():
    """读取配置"""
    return {
        "access_key_id": os.getenv("SMS_ACCESS_KEY_ID"),
        "access_key_secret": os.getenv("SMS_ACCESS_KEY_SECRET"),
        "sign_name": os.getenv("SMS_SIGN_NAME", "速通互联验证码"),
        "template_code": os.getenv("SMS_TEMPLATE_CODE", "100001"),
        "region": os.getenv("SMS_REGION", "cn-shenzhen"),
    }


async def send(phone: str):
    """发送验证码"""
    cfg = get_config()
    print("配置信息:")
    print(f"  Region:       {cfg['region']}")
    print(f"  SignName:     {cfg['sign_name']}")
    print(f"  TemplateCode: {cfg['template_code']}")
    print(f"  PhoneNumber:  {phone}")
    print()

    if not cfg["access_key_id"] or not cfg["access_key_secret"]:
        print("❌ 缺少 SMS_ACCESS_KEY_ID 或 SMS_ACCESS_KEY_SECRET")
        return None

    client = AcsClient(cfg["access_key_id"], cfg["access_key_secret"], cfg["region"])
    request = SendSmsVerifyCodeRequest()

    out_id = str(uuid4())
    request.set_SignName(cfg["sign_name"])
    request.set_TemplateCode(cfg["template_code"])
    request.set_PhoneNumber(phone)
    request.set_TemplateParam(json.dumps({"code": "##code##", "min": "5"}))
    request.set_OutId(out_id)

    print(f"📤 OutId: {out_id}")
    print("📤 正在发送（系统自动生成验证码）...")
    try:
        response = client.do_action_with_exception(request)
        result = json.loads(response)
        print(f"\n✅ API 响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get("Code") == "OK":
            print(f"\n✅ 短信已发送！OutId: {out_id}")
            return out_id
        else:
            print(f"\n❌ 发送失败 [{result.get('Code')}]: {result.get('Message')}")
            return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None


async def check(phone: str, code: str, out_id: str):
    """校验验证码"""
    cfg = get_config()
    client = AcsClient(cfg["access_key_id"], cfg["access_key_secret"], cfg["region"])
    request = CheckSmsVerifyCodeRequest()

    request.set_PhoneNumber(phone)
    request.set_VerifyCode(code)
    request.set_OutId(out_id)

    print(f"🔍 校验验证码: Phone={phone} Code={code} OutId={out_id}")
    try:
        response = client.do_action_with_exception(request)
        result = json.loads(response)
        print(f"\n📋 API 响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get("Code") == "OK":
            verify_result = result.get("Model", {}).get("VerifyResult", "")
            if verify_result == "PASS":
                print("\n✅ 验证码正确！")
            else:
                print(f"\n❌ 验证失败: {verify_result}")
        else:
            print(f"\n❌ 校验失败: {result.get('Message')}")
    except Exception as e:
        print(f"\n❌ 异常: {e}")


async def interactive(phone: str):
    """交互式完整流程"""
    out_id = await send(phone)
    if not out_id:
        return

    print("\n---\n")
    code = input("请输入收到的验证码: ").strip()
    if code:
        await check(phone, code, out_id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "send":
        phone = sys.argv[2] if len(sys.argv) > 2 else "15280766578"
        asyncio.run(send(phone))
    elif cmd == "check":
        phone = sys.argv[2]
        code = sys.argv[3]
        out_id = sys.argv[4]
        asyncio.run(check(phone, code, out_id))
    else:
        phone = cmd  # 直接传手机号 = 交互式流程
        asyncio.run(interactive(phone))
