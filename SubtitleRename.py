import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 尝试导入拖拽支持
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_ENABLED = True
except ImportError:
    DND_ENABLED = False
    print("警告：未安装 tkinterdnd2，将无法使用拖拽功能。请运行: pip install tkinterdnd2")

# 支持的视频和字幕扩展名
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
SUB_EXTS = {'.ass', '.ssa', '.srt', '.sub', '.vtt'}

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("视频字幕批量处理工具")
        self.root.geometry("750x550")
        self.root.resizable(True, True)

        # 选项卡容器
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 标签页1：匹配改名
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="匹配改名 (字幕复制)")

        # 标签页2：排序命名
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="排序命名 (集数重命名)")

        # 排序命名模板相关属性（新增 base 路径存储）
        self.base_prefix = ""
        self.base_suffix = ""
        self.base_digits = 0
        self.base_video_ext = ""
        self.base_sub_ext = ""
        self.base_video_path = ""   # 基础视频完整路径
        self.base_sub_path = ""     # 基础字幕完整路径

        # 初始化各标签页
        self.init_tab1()
        self.init_tab2()

    # ================== 标签页1：匹配改名 ==================
    def init_tab1(self):
        frame = self.tab1

        list_frame = ttk.LabelFrame(frame, text="拖入视频和字幕文件（自动排序配对）")
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 创建双列显示框架
        dual_list_frame = ttk.Frame(list_frame)
        dual_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 左侧视频列表
        video_frame = ttk.Frame(dual_list_frame)
        video_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        ttk.Label(video_frame, text="视频文件", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.video_listbox = tk.Listbox(video_frame, selectmode='extended', height=15)
        self.video_listbox.pack(side='left', fill='both', expand=True)
        video_scroll = ttk.Scrollbar(video_frame, orient='vertical', command=self.video_listbox.yview)
        video_scroll.pack(side='right', fill='y')
        self.video_listbox.config(yscrollcommand=video_scroll.set)
        
        # 右侧字幕列表
        sub_frame = ttk.Frame(dual_list_frame)
        sub_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        ttk.Label(sub_frame, text="字幕文件", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.sub_listbox = tk.Listbox(sub_frame, selectmode='extended', height=15)
        self.sub_listbox.pack(side='left', fill='both', expand=True)
        sub_scroll = ttk.Scrollbar(sub_frame, orient='vertical', command=self.sub_listbox.yview)
        sub_scroll.pack(side='right', fill='y')
        self.sub_listbox.config(yscrollcommand=sub_scroll.set)
        
        # 配置网格权重使两列等宽
        dual_list_frame.columnconfigure(0, weight=1)
        dual_list_frame.columnconfigure(1, weight=1)
        dual_list_frame.rowconfigure(0, weight=1)

        self.video_files = []  # 存储视频文件路径
        self.sub_files = []    # 存储字幕文件路径

        btn_frame1 = ttk.Frame(frame)
        btn_frame1.pack(fill='x', padx=5, pady=5)

        self.btn_rename1 = ttk.Button(btn_frame1, text="一键改名", command=self.rename_and_copy)
        self.btn_rename1.pack(side='left', padx=5)

        self.btn_delete1 = ttk.Button(btn_frame1, text="删除选中", command=self.delete_selected1)
        self.btn_delete1.pack(side='left', padx=5)

        self.btn_clear1 = ttk.Button(btn_frame1, text="一键清空", command=self.clear_list1)
        self.btn_clear1.pack(side='left', padx=5)

        self.status1 = ttk.Label(frame, text="就绪")
        self.status1.pack(side='bottom', fill='x', padx=5, pady=5)

        if DND_ENABLED:
            # 为两个列表框都绑定拖拽事件
            self.video_listbox.drop_target_register(DND_FILES)
            self.video_listbox.dnd_bind('<<Drop>>', self.on_drop_tab1)
            self.sub_listbox.drop_target_register(DND_FILES)
            self.sub_listbox.dnd_bind('<<Drop>>', self.on_drop_tab1)

    def on_drop_tab1(self, event):
        files = self.parse_drop_data(event.data)
        for f in files:
            if os.path.isfile(f):
                ext = os.path.splitext(f)[1].lower()
                # 检查是否是支持的文件类型
                if ext not in VIDEO_EXTS and ext not in SUB_EXTS:
                    messagebox.showwarning("不支持的文件", f"文件类型不支持: {os.path.basename(f)}")
                    continue
                    
                # 检查是否已存在重复文件
                all_files = self.video_files + self.sub_files
                if f in all_files:
                    messagebox.showwarning("重复文件", f"文件已存在: {os.path.basename(f)}")
                    continue
                    
                # 根据文件类型添加到对应列表
                if ext in VIDEO_EXTS:
                    self.video_files.append(f)
                    self.video_listbox.insert(tk.END, os.path.basename(f))
                elif ext in SUB_EXTS:
                    self.sub_files.append(f)
                    self.sub_listbox.insert(tk.END, os.path.basename(f))
        self.update_status1()

    def parse_drop_data(self, data):
        if data.startswith('{'):
            return re.findall(r'\{([^}]*)\}', data)
        else:
            return data.split()

    def update_status1(self):
        video_count = len(self.video_files)
        sub_count = len(self.sub_files)
        total_count = video_count + sub_count
        self.status1.config(text=f"已添加 {total_count} 个文件 (视频: {video_count}, 字幕: {sub_count})")

    def delete_selected1(self):
        # 获取选中的项目
        video_selected = self.video_listbox.curselection()
        sub_selected = self.sub_listbox.curselection()
        
        # 删除选中的视频文件
        for idx in sorted(video_selected, reverse=True):
            self.video_listbox.delete(idx)
            del self.video_files[idx]
            
        # 删除选中的字幕文件
        for idx in sorted(sub_selected, reverse=True):
            self.sub_listbox.delete(idx)
            del self.sub_files[idx]
            
        self.update_status1()

    def clear_list1(self):
        self.video_listbox.delete(0, tk.END)
        self.sub_listbox.delete(0, tk.END)
        self.video_files.clear()
        self.sub_files.clear()
        self.update_status1()

    def rename_and_copy(self):
        if not self.video_files and not self.sub_files:
            messagebox.showwarning("警告", "列表为空，请添加文件。")
            return

        videos = self.video_files[:]
        subs = self.sub_files[:]

        videos.sort(key=lambda p: os.path.basename(p))
        subs.sort(key=lambda p: os.path.basename(p))

        if len(videos) != len(subs):
            messagebox.showerror("数量不匹配",
                                 f"视频文件 {len(videos)} 个，字幕文件 {len(subs)} 个，数量必须相同才能改名！")
            return

        if not messagebox.askyesno("确认操作",
                                   f"将根据排序后的顺序进行配对（共{len(videos)}对），并把字幕复制到视频目录。是否继续？"):
            return

        success_count = 0
        skip_count = 0
        overwrite_all = False
        for video, sub in zip(videos, subs):
            video_dir = os.path.dirname(video)
            video_name = os.path.splitext(os.path.basename(video))[0]
            sub_ext = os.path.splitext(sub)[1]
            new_sub_name = video_name + sub_ext
            dest_path = os.path.join(video_dir, new_sub_name)

            if os.path.exists(dest_path):
                if overwrite_all:
                    pass
                else:
                    answer = messagebox.askyesnocancel("文件冲突",
                                                       f"文件已存在: {new_sub_name}\n是否覆盖？\n点“是”覆盖，点“否”跳过，点“取消”终止。")
                    if answer is None:
                        messagebox.showinfo("已取消", f"操作已取消，已处理 {success_count} 个文件。")
                        return
                    elif not answer:
                        skip_count += 1
                        continue
                    else:
                        overwrite_all = messagebox.askyesno("全部覆盖", "是否对所有冲突文件执行相同操作？")
            try:
                shutil.copy2(sub, dest_path)
                success_count += 1
            except Exception as e:
                messagebox.showerror("复制失败", f"复制 {os.path.basename(sub)} 失败:\n{e}")
                return

        result = f"完成！成功复制 {success_count} 个字幕文件。"
        if skip_count:
            result += f" 跳过 {skip_count} 个已存在的文件。"
        messagebox.showinfo("操作完成", result)
        self.clear_list1()

    # ================== 标签页2：排序命名 ==================
    def init_tab2(self):
        frame = self.tab2

        base_frame = ttk.LabelFrame(frame, text="1. 选择基础文件（模板）")
        base_frame.pack(fill='x', padx=5, pady=5)

        btn_select_base = ttk.Button(base_frame, text="选择基础文件", command=self.select_base_files)
        btn_select_base.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        self.lbl_video_base = ttk.Label(base_frame, text="视频：未选择", foreground="gray")
        self.lbl_video_base.grid(row=1, column=0, padx=5, sticky='w')
        self.lbl_sub_base = ttk.Label(base_frame, text="字幕：未选择", foreground="gray")
        self.lbl_sub_base.grid(row=2, column=0, padx=5, sticky='w')

        start_frame = ttk.Frame(frame)
        start_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(start_frame, text="起始数字:").pack(side='left')
        self.entry_start_num = ttk.Entry(start_frame, width=10)
        self.entry_start_num.insert(0, "1")
        self.entry_start_num.pack(side='left', padx=5)

        list_frame2 = ttk.LabelFrame(frame, text="2. 拖入待重命名的多对视频和字幕文件")
        list_frame2.pack(fill='both', expand=True, padx=5, pady=5)

        self.listbox2 = tk.Listbox(list_frame2, selectmode='extended', height=12)
        self.listbox2.pack(side='left', fill='both', expand=True, padx=(5, 5), pady=5)
        scroll2 = ttk.Scrollbar(list_frame2, orient='vertical', command=self.listbox2.yview)
        scroll2.pack(side='right', fill='y')
        self.listbox2.config(yscrollcommand=scroll2.set)
        self.files2 = []

        btn_frame2 = ttk.Frame(frame)
        btn_frame2.pack(fill='x', padx=5, pady=5)

        self.btn_rename2 = ttk.Button(btn_frame2, text="排序命名", command=self.sort_rename)
        self.btn_rename2.pack(side='left', padx=5)

        self.btn_delete2 = ttk.Button(btn_frame2, text="删除选中", command=self.delete_selected2)
        self.btn_delete2.pack(side='left', padx=5)

        self.btn_clear2 = ttk.Button(btn_frame2, text="清空列表", command=self.clear_list2)
        self.btn_clear2.pack(side='left', padx=5)

        self.status2 = ttk.Label(frame, text="就绪")
        self.status2.pack(side='bottom', fill='x', padx=5, pady=5)

        if DND_ENABLED:
            self.listbox2.drop_target_register(DND_FILES)
            self.listbox2.dnd_bind('<<Drop>>', self.on_drop_tab2)

    def on_drop_tab2(self, event):
        files = self.parse_drop_data(event.data)
        for f in files:
            if os.path.isfile(f):
                self.files2.append(f)
                self.listbox2.insert(tk.END, os.path.basename(f))
        self.update_status2()

    def update_status2(self):
        count = len(self.files2)
        self.status2.config(text=f"已添加 {count} 个文件")

    def delete_selected2(self):
        selected = self.listbox2.curselection()
        if not selected:
            return
        for idx in sorted(selected, reverse=True):
            self.listbox2.delete(idx)
            del self.files2[idx]
        self.update_status2()

    def clear_list2(self):
        self.listbox2.delete(0, tk.END)
        self.files2.clear()
        self.update_status2()

    def select_base_files(self):
        video_path = filedialog.askopenfilename(
            title="选择基础视频文件",
            filetypes=[("视频文件", "*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm"), ("所有文件", "*.*")]
        )
        if not video_path:
            return
        dir_name = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        candidates = []
        for ext in SUB_EXTS:
            candidate = os.path.join(dir_name, base_name + ext)
            if os.path.isfile(candidate):
                candidates.append(candidate)
        if len(candidates) == 0:
            sub_path = filedialog.askopenfilename(
                title="未找到匹配字幕，请手动选择",
                filetypes=[("字幕文件", "*.ass;*.ssa;*.srt;*.sub;*.vtt"), ("所有文件", "*.*")]
            )
            if not sub_path:
                messagebox.showwarning("警告", "未选择字幕文件，操作取消。")
                return
            sub_path = sub_path
        elif len(candidates) == 1:
            sub_path = candidates[0]
        else:
            sub_path = filedialog.askopenfilename(
                title="找到多个匹配字幕，请选择",
                initialdir=dir_name,
                filetypes=[("字幕文件", "*.ass;*.ssa;*.srt;*.sub;*.vtt"), ("所有文件", "*.*")]
            )
            if not sub_path:
                return

        video_name = os.path.splitext(os.path.basename(video_path))[0]
        digits = self.extract_digits_pattern(video_name)
        if digits is None:
            messagebox.showerror("错误", "无法从基础文件名中识别出独立数字部分（如 [38]）。请确认文件名格式。")
            return

        self.base_prefix = video_name[:digits['start']]
        self.base_suffix = video_name[digits['end']:]
        self.base_digits = digits['length']
        self.base_video_ext = os.path.splitext(video_path)[1]
        self.base_sub_ext = os.path.splitext(sub_path)[1]
        # 保存完整路径（优化新增）
        self.base_video_path = video_path
        self.base_sub_path = sub_path

        self.lbl_video_base.config(text=f"视频：{os.path.basename(video_path)}", foreground="black")
        self.lbl_sub_base.config(text=f"字幕：{os.path.basename(sub_path)}", foreground="black")

        preview_number = "01" if self.base_digits == 2 else str(1).zfill(self.base_digits)
        preview_name = self.base_prefix + preview_number + self.base_suffix
        self.status2.config(text=f"模板已设置 | 文件将移动到: {os.path.dirname(video_path)} | 预览: {preview_name}.ext")

    def extract_digits_pattern(self, filename):
        matches = list(re.finditer(r'(?<![a-zA-Z0-9])\d+(?![a-zA-Z0-9])', filename))
        if not matches:
            return None
        match = matches[0]
        return {
            'start': match.start(),
            'end': match.end(),
            'length': len(match.group()),
            'value': match.group()
        }

    def sort_rename(self):
        # 检查模板是否已设置
        if not self.base_video_path:
            messagebox.showerror("错误", "请先选择基础文件模板。")
            return

        if not self.files2:
            messagebox.showerror("错误", "待重命名列表为空，请拖入文件。")
            return

        start_str = self.entry_start_num.get().strip()
        if not start_str.isdigit():
            messagebox.showerror("错误", "起始数字必须为正整数。")
            return
        start_num = int(start_str)
        if start_num < 0:
            messagebox.showerror("错误", "起始数字不能为负数。")
            return

        # 分离视频与字幕
        videos = []
        subs = []
        for path in self.files2:
            ext = os.path.splitext(path)[1].lower()
            if ext in VIDEO_EXTS:
                videos.append(path)
            elif ext in SUB_EXTS:
                subs.append(path)
            else:
                messagebox.showerror("不支持的文件", f"文件类型不支持: {os.path.basename(path)}")
                return

        videos.sort(key=lambda p: os.path.basename(p))
        subs.sort(key=lambda p: os.path.basename(p))

        if len(videos) != len(subs):
            messagebox.showerror("数量不匹配",
                                 f"视频 {len(videos)} 个，字幕 {len(subs)} 个，数量必须相同才能批量重命名！")
            return

        # 目标文件夹：基础视频所在的文件夹
        target_dir = os.path.dirname(self.base_video_path)
        pairs_count = len(videos)

        if not messagebox.askyesno("确认重命名并移动",
                                   f"将按照模板格式重命名 {pairs_count} 对文件，\n"
                                   f"并移动到文件夹:\n{target_dir}\n\n"
                                   f"起始数字: {start_num}\n"
                                   f"此操作不可撤销，是否继续？"):
            return

        renamed = 0
        for idx, (video, sub) in enumerate(zip(videos, subs)):
            new_number = str(start_num + idx).zfill(self.base_digits)
            video_ext = os.path.splitext(video)[1]
            sub_ext = os.path.splitext(sub)[1]
            new_video_name = self.base_prefix + new_number + self.base_suffix + video_ext
            new_sub_name = self.base_prefix + new_number + self.base_suffix + sub_ext

            new_video_path = os.path.join(target_dir, new_video_name)
            new_sub_path = os.path.join(target_dir, new_sub_name)

            # 如果源文件已经位于目标路径且名称相同，跳过（无需操作）
            if os.path.normcase(video) == os.path.normcase(new_video_path) and \
               os.path.normcase(sub) == os.path.normcase(new_sub_path):
                renamed += 1
                continue

            # 冲突检查（视频或字幕目标已存在且不是源文件本身）
            conflict_video = os.path.exists(new_video_path) and os.path.normcase(video) != os.path.normcase(new_video_path)
            conflict_sub = os.path.exists(new_sub_path) and os.path.normcase(sub) != os.path.normcase(new_sub_path)

            if conflict_video or conflict_sub:
                conflict_names = []
                if conflict_video:
                    conflict_names.append(new_video_name)
                if conflict_sub:
                    conflict_names.append(new_sub_name)
                if not messagebox.askyesno("文件冲突",
                                           f"目标文件已存在：\n{chr(10).join(conflict_names)}\n是否覆盖？\n点“否”将跳过这一对文件。"):
                    continue

            try:
                # 移动/重命名文件到目标目录
                shutil.move(video, new_video_path)
                shutil.move(sub, new_sub_path)
                renamed += 1
            except Exception as e:
                messagebox.showerror("移动失败", f"移动文件时出错:\n{e}")
                return

        messagebox.showinfo("完成", f"成功重命名并移动 {renamed} 对文件到:\n{target_dir}")
        self.clear_list2()


if __name__ == "__main__":
    if DND_ENABLED:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = App(root)
    root.mainloop()