"""简历脱敏：自动识别并替换敏感个人信息，防止隐私泄露。"""
from __future__ import annotations

import re


class ResumeDesensitizer:
    """识别并脱敏简历中的个人隐私信息。"""

    # 姓名识别：中文全名 + 英文名
    NAME_PATTERNS = [
        re.compile(r"^姓名[：:\s]*(.+?)$", re.M),
        re.compile(r"^(.{2,4})\s*$", re.M),  # 单行2-4个汉字（弱规则，用其他字段辅助）
    ]

    # 手机号：11位手机号
    PHONE_PATTERNS = [
        re.compile(r"1[3-9]\d{9}"),
        re.compile(r"\+?86\s*1[3-9]\d\s*\d{3}\s*\d{4}"),
    ]

    # 邮箱
    EMAIL_PATTERNS = [
        re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    ]

    # 微信号
    WECHAT_PATTERNS = [
        re.compile(r"微信[：:\s]*([A-Za-z0-9_-]{6,20})"),
        re.compile(r"WeChat[：:\s]*([A-Za-z0-9_-]{6,20})"),
        re.compile(r"wx[a-zA-Z0-9_-]{5,}"),
    ]

    # 身份证号
    ID_CARD_PATTERNS = [
        re.compile(r"\d{17}[\dXx]"),
    ]

    # 地址
    ADDRESS_PATTERNS = [
        re.compile(r"现居住地[：:\s]*(.+?)$", re.M),
        re.compile(r"地址[：:\s]*(.+?)$", re.M),
    ]

    # 毕业院校（含个人信息标识）
    SCHOOL_PATTERNS = [
        re.compile(r"^(.{2,10}(?:大学|学院|学校))\s*([^\s]+)?", re.M),
    ]

    def __init__(self) -> None:
        self.masked_fields: dict[str, str] = {}

    def mask(self, text: str) -> tuple[str, dict]:
        """
        对简历文本进行脱敏处理。

        Returns:
            (脱敏后的文本, 被脱敏的字段对照表)
        """
        result = text
        self.masked_fields = {}
        mask_counter = 0

        # 手机号 - 最优先处理
        for p in self.PHONE_PATTERNS:
            for m in p.finditer(result):
                phone = m.group()
                masked = f"***MASK_PHONE{mask_counter}***"
                result = result.replace(phone, masked, 1)
                self.masked_fields[masked] = self._mask_phone(phone)
                mask_counter += 1

        # 邮箱
        for p in self.EMAIL_PATTERNS:
            for m in p.finditer(result):
                email = m.group()
                masked = f"***MASK_EMAIL{mask_counter}***"
                result = result.replace(email, masked, 1)
                self.masked_fields[masked] = f"[邮箱已脱敏]"
                mask_counter += 1

        # 微信号
        for p in self.WECHAT_PATTERNS:
            for m in p.finditer(result):
                wechat = m.group()
                masked = f"***MASK_WECHAT{mask_counter}***"
                result = result.replace(wechat, masked, 1)
                self.masked_fields[masked] = "[微信已脱敏]"
                mask_counter += 1

        # 身份证号
        for p in self.ID_CARD_PATTERNS:
            for m in p.finditer(result):
                id_card = m.group()
                masked = f"***MASK_ID{mask_counter}***"
                result = result.replace(id_card, masked, 1)
                self.masked_fields[masked] = "[身份证号已脱敏]"
                mask_counter += 1

        # 姓名 - 放在最后处理，避免被其他规则误伤
        # 优先匹配 "姓名：张三" 格式
        name_match = re.search(r"姓名[：:\s]*([\u4e00-\u9fa5a-zA-Z]{2,10})", result)
        if name_match:
            name = name_match.group(1)
            result = result.replace(name, "[姓名已脱敏]", 1)
            self.masked_fields["[姓名已脱敏]"] = f"原名: {name}"

        return result, self.masked_fields

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """手机号只保留前三位和后四位。"""
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 11:
            return f"{digits[:3]}****{digits[-4:]}"
        return "***"

    def get_mask_summary(self) -> str:
        """生成脱敏摘要，说明脱敏了哪些内容。"""
        if not self.masked_fields:
            return "（未发现敏感信息）"
        parts = []
        seen_values = set()
        for masked, original in self.masked_fields.items():
            if original not in seen_values:
                parts.append(original)
                seen_values.add(original)
        return "；".join(parts)


if __name__ == "__main__":
    test_resume = """
    姓名：李明
    手机：13812345678
    邮箱：liming_email@163.com
    微信：liming001

    工作经历
    公司：某某科技
    职位：用户运营经理
    职责：负责用户增长和留存
    """
    desensitizer = ResumeDesensitizer()
    masked, summary = desensitizer.mask(test_resume)
    print("脱敏摘要：", summary)
    print("\n脱敏后文本：")
    print(masked)