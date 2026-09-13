import unittest

from core.utils.tenant_css import sanitize_tenant_css


class TenantCssSecurityTests(unittest.TestCase):
    def test_removes_markup_imports_and_executable_schemes(self):
        css = sanitize_tenant_css(
            "</style><script>alert(1)</script>"
            "@import url(https://example.invalid);"
            "a{background:url(javascript:alert(1));}"
        )
        lowered = css.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("</style", lowered)
        self.assertNotIn("@import", lowered)
        self.assertNotIn("javascript:", lowered)

    def test_limits_css_length(self):
        self.assertEqual(len(sanitize_tenant_css("x" * 30_000)), 20_000)
