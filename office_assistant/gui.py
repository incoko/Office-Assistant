from __future__ import annotations

import json
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    TK_AVAILABLE = True
    TK_IMPORT_ERROR = None
except ImportError as exc:  # Frozen build must bundle Tk; source environments may lack it.
    tk = None
    filedialog = messagebox = ttk = None
    TK_AVAILABLE = False
    TK_IMPORT_ERROR = exc
import uuid

from . import __version__
from .llm import MockModelClient
from .mcp import MockMcpClient
from .model_service import ModelService
from .models import AgentProfile, ModelConnection
from .runtime import AgentRuntime
from .scenarios import check_spreadsheets, draft_document, fingerprint, query_policy
from .store import JsonStore


if not TK_AVAILABLE:
    class OfficeAssistantApp:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("当前运行环境缺少 Tk。开发环境需配置 Tk；安装版应自带 Tk，请重新构建或联系维护人员。") from TK_IMPORT_ERROR

    def run_app():
        raise RuntimeError("当前运行环境缺少 Tk。开发环境需配置 Tk；安装版应自带 Tk，请重新构建或联系维护人员。") from TK_IMPORT_ERROR
else:
    class OfficeAssistantApp(tk.Tk):
        def __init__(self, store: JsonStore | None = None):
            super().__init__()
            self.title(f"Office Assistant {__version__} - 内网办公助手")
            self.geometry("1100x720")
            self.store = store or JsonStore()
            self.model_service = ModelService(self.store)
            self.runtime = AgentRuntime(self.store, MockModelClient("本地模拟模型已返回结果。"))
            self.mcp = MockMcpClient()
            self.selected_agent = self._ensure_default_agent()
            self._build()
    
        def _ensure_default_agent(self) -> AgentProfile:
            agents = self.store.agents()
            if agents:
                return agents[0]
            agent = AgentProfile(str(uuid.uuid4()), "办公助手", "你是一个严谨的银行办公材料助手。只根据用户提供的材料回答，缺失信息标记待补充。")
            self.store.save_agent(agent)
            return agent
    
        def _build(self):
            self.columnconfigure(1, weight=1); self.rowconfigure(0, weight=1)
            nav = ttk.Frame(self, padding=12); nav.grid(row=0, column=0, sticky="ns")
            ttk.Label(nav, text="办公助手", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 20))
            for title, callback in [("通用对话", self.show_chat), ("写周报 / 纪要", self.show_drafting), ("汇总 / 检查表格", self.show_spreadsheet), ("查制度 / 找依据", self.show_policy), ("高级设置", self.show_settings)]:
                ttk.Button(nav, text=title, command=callback, width=22).pack(anchor="w", pady=4)
            ttk.Label(nav, text="\n目标部署环境\nWindows 10 x64\n模拟服务模式", foreground="#666").pack(anchor="w", pady=20)
            self.content = ttk.Frame(self, padding=20); self.content.grid(row=0, column=1, sticky="nsew")
            self.show_home()
    
        def _clear(self):
            for child in self.content.winfo_children(): child.destroy()
    
        def show_home(self):
            self._clear(); ttk.Label(self.content, text="欢迎使用办公助手", font=("Segoe UI", 24, "bold")).pack(anchor="w")
            ttk.Label(self.content, text="选择一个任务入口，或在高级设置中配置智能体、Skill 和 MCP。\n当前界面使用本地模拟模型，真实内网服务将在部署测试阶段接入。", justify="left").pack(anchor="w", pady=12)
            self.show_cards()
    
        def show_cards(self):
            frame=ttk.Frame(self.content); frame.pack(fill="x", pady=20)
            for label, callback, desc in [("写周报 / 纪要", self.show_drafting, "根据工作记录生成待复核草稿"),("汇总 / 检查表格", self.show_spreadsheet, "合并固定模板并定位问题"),("查制度 / 找依据", self.show_policy, "检索本地制度并展示来源")]:
                box=ttk.LabelFrame(frame, text=label, padding=12); box.pack(side="left", fill="both", expand=True, padx=5)
                ttk.Label(box, text=desc, wraplength=200).pack(anchor="w"); ttk.Button(box,text="开始",command=callback).pack(anchor="w",pady=12)
    
        def _configured_connection(self):
            connection_id = self.selected_agent.model_connection_id
            return self.model_service.by_id(connection_id)

        def _runtime_for_agent(self):
            connection = self._configured_connection()
            if connection is None:
                raise RuntimeError("尚未配置内网模型。请先打开“高级设置”，填写模型地址和模型名称并测试连接。")
            return AgentRuntime(self.store, self.model_service.client(connection))

        def show_chat(self):
            self._clear(); ttk.Label(self.content,text="通用对话",font=("Segoe UI",20,"bold")).pack(anchor="w")
            connection = self._configured_connection()
            model_text = f"模型：{connection.model}（{connection.base_url}）" if connection else "模型：尚未配置"
            ttk.Label(self.content,text=f"当前智能体：{self.selected_agent.name}    {model_text}").pack(anchor="w",pady=8)
            prompt=tk.Text(self.content,height=8); prompt.pack(fill="x")
            output=tk.Text(self.content,height=18,state="disabled"); output.pack(fill="both",expand=True,pady=10)
            messages = []
            def append(role, text):
                messages.append({"role": role, "content": text})
                output.configure(state="normal")
                output.insert("end", f"{"你" if role == "user" else "助手"}：\n{text}\n\n")
                output.see("end")
                output.configure(state="disabled")
            def run():
                text = prompt.get("1.0","end").strip()
                if not text:
                    messagebox.showinfo("提示", "请输入要发送的内容。")
                    return
                try:
                    runtime = self._runtime_for_agent()
                    messages_for_request = messages + [{"role": "user", "content": text}]
                    task = runtime.run(self.selected_agent, "通用对话", text, messages=messages_for_request)
                    response = next((event["message"] for event in reversed(task.events) if event["kind"] == "assistant_message"), None)
                    if task.status.value != "succeeded" or response is None:
                        raise RuntimeError(task.error or "模型没有返回可显示的内容")
                    append("user", text)
                    append("assistant", response)
                    prompt.delete("1.0", "end")
                except Exception as exc:
                    messagebox.showerror("发送失败", str(exc))
            ttk.Button(self.content,text="发送",command=run).pack(anchor="e")
            if connection is None:
                ttk.Label(self.content,text="请先在高级设置配置 vLLM / OpenAI 兼容接口。",foreground="#805000").pack(anchor="e",pady=4)

        def show_drafting(self):
            self._clear(); ttk.Label(self.content,text="写周报 / 会议纪要",font=("Segoe UI",20,"bold")).pack(anchor="w")
            selected=tk.StringVar(); ttk.Entry(self.content,textvariable=selected).pack(fill="x",pady=8)
            output=tk.Text(self.content,height=25); output.pack(fill="both",expand=True)
            def choose(): selected.set(filedialog.askopenfilename(filetypes=[("Text/Word", "*.txt *.md *.docx")]))
            def run():
                try: output.delete("1.0","end"); output.insert("end",draft_document(selected.get(),"周报"))
                except Exception as exc: messagebox.showerror("无法处理",str(exc))
            ttk.Button(self.content,text="选择材料",command=choose).pack(side="left"); ttk.Button(self.content,text="生成草稿",command=run).pack(side="left",padx=8)
    
        def show_spreadsheet(self):
            from .spreadsheet_view import SpreadsheetPage
            self._clear()
            self.spreadsheet_page = SpreadsheetPage(self.content)
            self.spreadsheet_page.pack(fill="both", expand=True)

        def show_policy(self):
            self._clear(); ttk.Label(self.content,text="查制度 / 找依据",font=("Segoe UI",20,"bold")).pack(anchor="w")
            selected=tk.StringVar(); ttk.Entry(self.content,textvariable=selected).pack(fill="x",pady=8)
            query=tk.StringVar(); ttk.Entry(self.content,textvariable=query).pack(fill="x",pady=8); query.set("归档材料")
            output=tk.Text(self.content,height=25); output.pack(fill="both",expand=True)
            files=[]
            def choose():
                nonlocal files; files=list(filedialog.askopenfilenames(filetypes=[("Documents", "*.docx *.md *.txt")])) ; selected.set("; ".join(files))
            def run():
                try: output.delete("1.0","end"); output.insert("end",json.dumps(query_policy(files,query.get()),ensure_ascii=False,indent=2))
                except Exception as exc: messagebox.showerror("无法处理",str(exc))
            ttk.Button(self.content,text="导入制度",command=choose).pack(side="left"); ttk.Button(self.content,text="查询",command=run).pack(side="left",padx=8)
    
        def show_settings(self):
            self._clear(); ttk.Label(self.content,text="高级设置",font=("Segoe UI",20,"bold")).pack(anchor="w")
            ttk.Label(self.content,text=f"当前版本：{__version__}\n配置保存在当前用户目录；API Key 不写入普通 JSON 配置。\n本版本按 vLLM 的 OpenAI 兼容 Chat Completions 接口测试。",justify="left").pack(anchor="w",pady=12)
            box = ttk.LabelFrame(self.content, text="内网模型连接", padding=12); box.pack(fill="x", pady=8)
            box.columnconfigure(1, weight=1)
            connection = self._configured_connection()
            values = {
                "name": tk.StringVar(value=connection.name if connection else "内网 Qwen3.6"),
                "url": tk.StringVar(value=connection.base_url if connection else "http://127.0.0.1:8000/v1"),
                "model": tk.StringVar(value=connection.model if connection else "Qwen3.6"),
                "timeout": tk.StringVar(value=str(connection.timeout_seconds if connection else 60)),
                "key": tk.StringVar(value=""),
            }
            fields = [("名称", "name"), ("服务地址", "url"), ("模型名称", "model"), ("超时（秒）", "timeout"), ("API Key（可选）", "key")]
            for row, (label, key) in enumerate(fields):
                ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
                entry = ttk.Entry(box, textvariable=values[key], show="*" if key == "key" else "")
                entry.grid(row=row, column=1, sticky="ew", pady=4)
            result = tk.StringVar(value="")
            ttk.Label(box, textvariable=result, wraplength=700).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 4))
            def build_connection():
                try:
                    timeout = int(values["timeout"].get())
                    if timeout < 1 or timeout > 600:
                        raise ValueError("超时必须在 1 到 600 秒之间")
                    return ModelConnection(connection.id if connection else str(uuid.uuid4()), values["name"].get().strip() or "内网模型", values["url"].get().strip(), values["model"].get().strip(), connection.credential_ref if connection else None, timeout)
                except ValueError as exc:
                    raise ValueError(f"连接配置无效：{exc}")
            def test_connection():
                try:
                    candidate = build_connection()
                    if not candidate.base_url or not candidate.model:
                        raise ValueError("服务地址和模型名称不能为空")
                    checked = self.model_service.check(candidate, values["key"].get().strip() or None)
                    result.set(("✓ " if checked.ok else "✗ ") + checked.message)
                except Exception as exc:
                    result.set("✗ " + str(exc))
            def save_connection():
                try:
                    candidate = build_connection()
                    if not candidate.base_url or not candidate.model:
                        raise ValueError("服务地址和模型名称不能为空")
                    self.model_service.save_connection(candidate, values["key"].get().strip() or None)
                    self.selected_agent.model_connection_id = candidate.id
                    self.selected_agent.version += 1
                    self.store.save_agent(self.selected_agent)
                    result.set("✓ 配置已保存。现在可以打开“通用对话”发送消息。API Key 仅保存为当前用户的受保护凭据引用。")
                except Exception as exc:
                    result.set("✗ 保存失败：" + str(exc))
            actions = ttk.Frame(box); actions.grid(row=len(fields)+1, column=0, columnspan=2, sticky="w", pady=(8, 0))
            ttk.Button(actions,text="测试连接",command=test_connection).pack(side="left")
            ttk.Button(actions,text="保存配置",command=save_connection).pack(side="left", padx=8)
            ttk.Label(self.content,text="连接测试会调用服务的 /models；发送消息会调用 /chat/completions。当前先支持非流式收发，真实地址需在内网环境测试。",foreground="#666",wraplength=740).pack(anchor="w",pady=8)

    def run_app():
        app=OfficeAssistantApp(); app.mainloop()
