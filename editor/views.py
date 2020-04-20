from django.shortcuts import render

from contextlib import contextmanager
import io
import os
import subprocess
import sys
import traceback
from django.conf import settings
from django.views import generic
from .forms import EditorForm
 
 
@contextmanager
def stdoutIO():
    """一時的にstdoutを変更する"""
 
    old = sys.stdout
    sys.stdout = io.StringIO()
    yield sys.stdout
    sys.stdout = old
 
 
def execute_python_exec(code):
    """pythonコードをexecで評価し、出力を返す
 
    引数:
        code: Pythonコードの文字列
 
    返り値:
        出力とエラーの文字列
    """
 
    output = ''
    with stdoutIO() as stdout:
        error = ''
        try:
            exec(code)
        except:
            error = traceback.format_exc()
        finally:
            output = stdout.getvalue() + error
    return output
 
 
def execute_python_subprocess(file_path, python_path=sys.executable, timeout=15):
    """python file_path を行い、出力を返す
 
    引数:
        file_path: pythonファイルのパス
        python_path: pythonインタプリタのパス。デフォルトはこのDjangoを実行しているPythonインタプリタ
        timeout: プログラムの実行を何秒まで待つか。デフォルトは15秒
 
    返り値:
        出力とエラーの文字列
    """
 
    cmd = f'{python_path} {file_path}'
    ret = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, encoding='cp932')
    return ret.stdout
 
 
class Home(generic.FormView):
    template_name = 'editor/home.html'
    form_class = EditorForm
 
    def get_current_dirpath(self):
        """エディタの、現在のディレクトリパスを取得する"""
 
        # パラメータがなければ、manage.py があるディレクトリを返す
        current_path = self.request.GET.get('dir_path', settings.BASE_DIR)
 
        # ?dir_path= のような場合
        if not current_path:
            current_path = settings.BASE_DIR
 
        # もしもファイルだった場合は、そのディレクトリのパスに
        if os.path.isfile(current_path):
            current_path = os.path.dirname(current_path)
 
        return current_path
 
    def get_context_data(self, **kwargs):
        """contextの取得。アクセスされれば常に呼び出される"""
 
        # エディタの、現在表示すべきディレクトリパスを取得
        current_path = self.get_current_dirpath()
 
        # ディレクトリや全てのファイルの名前が入る
        files_and_dirs = os.listdir(current_path)
 
        # dirnameで前のフォルダを表せます
        before_dir = ('前のフォルダ', os.path.dirname(current_path))
 
        # ファイル一覧とディレクトリ一覧の作成処理
        files = []
        dirs = [before_dir]
        for path in files_and_dirs:
            path = os.path.join(current_path, path)
            basename = os.path.basename(path)
            if os.path.isdir(path):
                dirs.append((basename, path))
            else:
                files.append((basename, path))
 
        # contextのアップデート。{{ current_path }}等が使えるようになる
        extra_context = {
            'current_path': current_path,
            'dirs': dirs,
            'files': files,
        }
        kwargs.update(extra_context)
        return super().get_context_data(**kwargs)
 
    def get_initial(self):
        """formの初期値の取得
 
        &read_path=... パラメータがある場合は、そのファイルパスをopenで開き
        エディタのｺｰﾄﾞ入力欄へ移す。
        このread_pathパラメータが来るのは、画面左側の一覧からファイルをクリックした時だけ
        """
 
        try:
            path = self.request.GET['read_path']
        except KeyError:
            path = ''
            code = ''
        else:
            code = open(path, 'r', encoding='utf-8').read()
 
        initial = {
            'code': code,
            'file_name': os.path.basename(path),
        }
        return initial
 
    def run(self, form):
        """プログラムを実行する"""
 
        code = form.cleaned_data['code']
 
        # プログラムが空欄の場合は、実行しない
        if not code:
            output = '空欄です'
        else:
            current_path = self.get_current_dirpath()
            file_name = form.cleaned_data['file_name']
            file_path = os.path.join(current_path, file_name)
 
            # 何かファイルを開いているときは、pyton file_path を実行
            if file_name and os.path.isfile(file_path):
                output = execute_python_subprocess(file_path)
 
            # ファイルを開いてなければ、exec(code)を実行
            else:
                output = execute_python_exec(code)
 
        context = self.get_context_data(form=form, output=output)
        return self.render_to_response(context)
 
    def save(self, form):
        """プログラムの新規保存・上書き保存を行う"""
 
        output = ''
        file_name = form.cleaned_data['file_name']
 
        # ファイルを新規作成か、上書き保存の処理
        if file_name:
            current_path = self.get_current_dirpath()
            file_path = os.path.join(current_path, file_name)
            code = form.cleaned_data['code']
            with open(file_path, 'w') as file:
                file.write(code)
                output = f'{file_path}を保存しました'
        else:
            output = 'ファイル名を入力するか、　何かファイルを開いてください'
        context = self.get_context_data(form=form, output=output)
        return self.render_to_response(context)
 
    def form_valid(self, form):
        """Run、又はSaveを押した際に呼び出される"""
 
        if 'run' in self.request.POST:
            return self.run(form)
        elif 'save' in self.request.POST:
            return self.save(form)