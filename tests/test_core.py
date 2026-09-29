from pathlib import Path
import tempfile
import unittest

from office_assistant.llm import ChatResult, MockModelClient, ToolCall
from office_assistant.mcp import McpTool, MockMcpClient
from office_assistant.models import AgentProfile
from office_assistant.runtime import AgentRuntime
from office_assistant.scenarios import check_spreadsheets, draft_document, fingerprint, query_policy
from office_assistant.security import NetworkPolicy
from office_assistant.store import JsonStore

ROOT = Path(__file__).parents[1]
SAMPLES = ROOT / "samples"


class CoreTests(unittest.TestCase):
    def test_network_policy_allows_only_loopback_or_explicit_target(self):
        policy = NetworkPolicy.from_urls(["http://intranet.example:8080/sse"])
        self.assertTrue(policy.check_url("http://intranet.example:8080/sse")[0])
        self.assertFalse(policy.check_url("http://intranet.example:8080/other")[0])
        self.assertFalse(policy.check_url("https://example.com")[0])

    def test_runtime_rejects_unenabled_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp))
            agent = AgentProfile("a", "test", "test", enabled_tool_names=["demo_lookup"])
            store.save_agent(agent)
            model = MockModelClient(sequence=[ChatResult("", [ToolCall("demo_lookup", {"key": "x"})], {}), ChatResult("done", [], {})])
            runtime = AgentRuntime(store, model)
            mcp = MockMcpClient([McpTool("demo_lookup", "demo", {"type": "object"})])
            runtime.register_mcp_tools(mcp.list_tools(), mcp)
            task = runtime.run(agent, "test", "call tool")
            self.assertEqual(task.status.value, "failed")
            self.assertEqual(len(mcp.calls), 0)

    def test_runtime_calls_enabled_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp))
            agent = AgentProfile("a", "test", "test", enabled_tool_names=["demo_lookup"])
            model = MockModelClient(sequence=[ChatResult("", [ToolCall("demo_lookup", {"key": "x"})], {}), ChatResult("done", [], {})])
            runtime = AgentRuntime(store, model)
            mcp = MockMcpClient([McpTool("demo_lookup", "demo", {"type": "object"})])
            runtime.register_mcp_tools(mcp.list_tools(), mcp)
            runtime.enable_tool("demo_lookup")
            task = runtime.run(agent, "test", "call tool", authorized_tool_names=["demo_lookup"])
            self.assertEqual(task.status.value, "succeeded")
            self.assertEqual(mcp.calls, [("demo_lookup", {"key": "x"})])

    def test_sample_spreadsheets(self):
        result = check_spreadsheets([
            str(SAMPLES / "02-表格汇总/演示东网点.xlsx"),
            str(SAMPLES / "02-表格汇总/演示西网点.xlsx"),
        ])
        self.assertEqual(len(result["rows"]), 6)
        self.assertEqual(result["raw_totals"], {"应完成人数": 55, "已完成人数": 41, "未完成人数": 15})
        messages = "\n".join(issue["message"] for issue in result["issues"])
        self.assertIn("缺少必填字段：负责人", messages)
        self.assertIn("事项编号重复：DEMO-003", messages)
        self.assertIn("截止日期不是合法", messages)
        self.assertIn("人数不平", messages)

    def test_sample_document_and_policy(self):
        raw = SAMPLES / "01-文稿整理/原始工作记录.txt"
        draft = draft_document(str(raw))
        self.assertIn("待人工复核", draft)
        policy = SAMPLES / "03-制度查询/模拟培训归档制度.md"
        results = query_policy([str(policy)], "归档材料")
        self.assertTrue(results)
        self.assertEqual(len(fingerprint(str(policy))), 64)


if __name__ == "__main__":
    unittest.main()

class SpreadsheetPresentationTests(unittest.TestCase):
    def test_sample_result_is_user_readable_and_has_cell_locations(self):
        from office_assistant.spreadsheet_presentation import present_result
        result = check_spreadsheets([
            str(SAMPLES / "02-表格汇总/演示东网点.xlsx"),
            str(SAMPLES / "02-表格汇总/演示西网点.xlsx"),
        ])
        report = present_result(result)
        self.assertEqual(report.row_count, 6)
        self.assertEqual(report.totals, ("55", "41", "15"))
        self.assertTrue(report.has_issues)
        self.assertIn("4 组问题", report.status)
        details = "\n".join(problem.detail for problem in report.problems)
        self.assertIn("D3", details)
        self.assertIn("A4", details)
        self.assertIn("A3", details)
        self.assertIn("E4", details)
        self.assertIn("G4, H4, I4", details)
        self.assertIn("待核验原始合计", report.caution)

    def test_empty_selection_and_invalid_numeric_values_are_not_silent(self):
        from office_assistant.spreadsheet_presentation import present_result
        with self.assertRaises(ValueError):
            check_spreadsheets([])
        report = present_result({
            "rows": [object()],
            "issues": [{"type": "number", "message": "人数必须是非负整数", "source": "demo"}],
            "raw_totals": {"应完成人数": None, "已完成人数": 2, "未完成人数": 1},
        })
        self.assertEqual(report.totals, ("—", "2", "1"))
        self.assertIn("无法计算", report.caution)


class FileBoundaryTests(unittest.TestCase):
    def test_authorized_read_and_non_destructive_output(self):
        from office_assistant.file_access import AuthorizedFileAccess, FileAccessError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "authorized"
            root.mkdir()
            source = root / "input.txt"
            source.write_text("test", encoding="utf-8")
            output = root / "output"
            access = AuthorizedFileAccess([source], [root, output])
            self.assertEqual(access.authorize_read(source), source.resolve())
            existing = output / "result.txt"
            output.mkdir()
            existing.write_text("old", encoding="utf-8")
            created = access.write_new_text(output, "result.txt", "new")
            self.assertEqual(created.name, "result (1).txt")
            self.assertEqual(existing.read_text(encoding="utf-8"), "old")
            with self.assertRaises(FileAccessError):
                access.authorize_read(root.parent / "outside.txt")
            outside = root.parent / "outside-secret.txt"
            outside.write_text("secret", encoding="utf-8")
            link = root / "linked-secret.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(FileAccessError):
                    access.authorize_read(link)


class RuntimeValidationTests(unittest.TestCase):
    def test_invalid_tool_argument_is_rejected_before_mcp_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp))
            agent = AgentProfile("a", "test", "test", enabled_tool_names=["demo_lookup"])
            model = MockModelClient(requested_tool=ToolCall("demo_lookup", {"key": 123}))
            runtime = AgentRuntime(store, model)
            mcp = MockMcpClient([McpTool("demo_lookup", "demo", {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]})])
            runtime.register_mcp_tools(mcp.list_tools(), mcp)
            runtime.enable_tool("demo_lookup")
            task = runtime.run(agent, "test", "call tool", authorized_tool_names=["demo_lookup"])
            self.assertEqual(task.status.value, "failed")
            self.assertEqual(mcp.calls, [])


class ExtensionTests(unittest.TestCase):
    def test_skill_import_is_local_and_warns_about_scripts(self):
        from office_assistant.skills import SkillImporter
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "weekly"
            root.mkdir()
            (root / "SKILL.md").write_text("# 周报技能\ndescription: 仅整理工作记录\n", encoding="utf-8")
            (root / "helper.py").write_text("print('not executed')", encoding="utf-8")
            store = JsonStore(Path(tmp) / "data")
            result = SkillImporter(store).import_directory(root)
            self.assertEqual(result.package.name, "周报技能")
            self.assertTrue(any("可执行文件" in warning for warning in result.warnings))
            self.assertEqual(len(store.skills()), 1)

    def test_config_package_excludes_tasks_and_secrets(self):
        from office_assistant.config_io import ConfigPackage
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp) / "data")
            agent = AgentProfile("a", "test", "test")
            store.save_agent(agent)
            path = ConfigPackage.export(store, Path(tmp) / "config.json")
            payload = ConfigPackage.import_file(store, path)
            self.assertIn("agents", payload)
            self.assertNotIn("tasks", payload)
            self.assertNotIn("api_key", path.read_text(encoding="utf-8"))

class ModelConnectionTests(unittest.TestCase):
    def test_openai_compatible_client_sends_auth_and_receives_response(self):
        import json
        from unittest.mock import patch
        from office_assistant.llm import OpenAICompatibleClient
        seen = []
        class Response:
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(self.payload).encode()
        def fake_urlopen(request, timeout):
            seen.append((request.method, request.full_url, request.headers.get('Authorization'), json.loads(request.data.decode()) if request.data else None))
            if request.method == 'GET':
                return Response({'data': [{'id': 'Qwen3.6'}]})
            return Response({'choices': [{'message': {'role': 'assistant', 'content': '内网模型已回复'}}]})
        client = OpenAICompatibleClient('http://127.0.0.1:8000/v1', 'Qwen3.6', api_key='test-token')
        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            self.assertEqual(client.list_models()[0]['id'], 'Qwen3.6')
            response = client.chat([{'role': 'user', 'content': '你好'}])
        self.assertEqual(response.content, '内网模型已回复')
        self.assertEqual(seen[0][2], 'Bearer test-token')
        self.assertEqual(seen[1][2], 'Bearer test-token')
        self.assertEqual(seen[1][3]['model'], 'Qwen3.6')
        self.assertFalse(seen[1][3]['stream'])

    def test_model_service_state_does_not_contain_api_key(self):
        from office_assistant.model_service import ModelService
        from office_assistant.models import ModelConnection
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp))
            service = ModelService(store)
            service.save_connection(ModelConnection('m', 'test', 'http://127.0.0.1:8000/v1', 'Qwen3.6'), 'secret-token')
            state = (Path(tmp) / 'config/state.json').read_text(encoding='utf-8')
            self.assertNotIn('secret-token', state)
            self.assertNotIn('api_key', state)
            self.assertEqual(service.credentials.get(store.models()[0].credential_ref), 'secret-token')
