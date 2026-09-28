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

from .llm import MockModelClient
from .mcp import MockMcpClient
from .models import AgentProfile
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
            self.title("Office Assistant - 内网办公助手")
            self.geometry("1100x720")
            self.store = store or JsonStore()
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
            ttk.Label(nav, text="\n当前运行环境\nWindows 10 x64\n模拟服务模式", foreground="#666").pack(anchor="w", pady=20)
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
    
        def show_chat(self):
            self._clear(); ttk.Label(self.content,text="通用对话",font=("Segoe UI",20,"bold")).pack(anchor="w")
            ttk.Label(self.content,text=f"当前智能体：{self.selected_agent.name}").pack(anchor="w",pady=8)
            prompt=tk.Text(self.content,height=8); prompt.pack(fill="x")
            output=tk.Text(self.content,height=18,state="disabled"); output.pack(fill="both",expand=True,pady=10)
            def run():
                task=self.runtime.run(self.selected_agent,"通用对话",prompt.get("1.0","end").strip())
                output.configure(state="normal"); output.delete("1.0","end"); output.insert("end", next((event["message"] for event in reversed(task.events) if event["kind"] == "assistant_message"), task.error or "任务未产生回答")); output.configure(state="disabled")
            ttk.Button(self.content,text="执行（模拟模型）",command=run).pack(anchor="e")
    
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
            self._clear(); ttk.Label(self.content,text="汇总 / 检查表格",font=("Segoe UI",20,"bold")).pack(anchor="w")
            selected=tk.StringVar(); ttk.Entry(self.content,textvariable=selected).pack(fill="x",pady=8)
            output=tk.Text(self.content,height=25); output.pack(fill="both",expand=True)
            files=[]
            def choose():
                nonlocal files; files=list(filedialog.askopenfilenames(filetypes=[("Excel", "*.xlsx")])) ; selected.set("; ".join(files))
            def run():
                try:
                    result=check_spreadsheets(files); output.delete("1.0","end"); output.insert("end",json.dumps({"raw_totals":result["raw_totals"],"issues":result["issues"]},ensure_ascii=False,indent=2))
                except Exception as exc: messagebox.showerror("无法处理",str(exc))
            ttk.Button(self.content,text="选择表格",command=choose).pack(side="left"); ttk.Button(self.content,text="检查",command=run).pack(side="left",padx=8)
    
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
            ttk.Label(self.content,text="当前版本：0.1.0\n模型：本地模拟模型\nMCP：模拟工具（默认未授权）\n真实 vLLM / SSE MCP 将在部署测试阶段配置。",justify="left").pack(anchor="w",pady=12)
            ttk.Label(self.content,text="智能体配置（当前本地存储）").pack(anchor="w")
            for agent in self.store.agents(): ttk.Label(self.content,text=f"• {agent.name} / {agent.id}").pack(anchor="w")
    
    
    def run_app():
        app=OfficeAssistantApp(); app.mainloop()
