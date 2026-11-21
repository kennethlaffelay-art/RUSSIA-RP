from pathlib import Path
import re,sys
p=next(Path(sys.argv[1]).rglob('Downloader$DownloadFilesTask.smali')); s=p.read_text()
task='Lblackrussia/online/Downloader$DownloadFilesTask;'
helper='Lru/russiarp/install/StockCache;'
signature='.method protected varargs doInBackground([Ljava/io/File;)Ljava/lang/Integer;'
start=s.index(signature);end=s.index('.end method',start)
s=s[:start]+f'''{signature}
    .locals 1
    iget-object v0, p0, {task}->this$0:Lblackrussia/online/Downloader;
    invoke-static {{v0, p0}}, {helper}->run(Landroid/app/Activity;Landroid/os/AsyncTask;)Ljava/lang/Integer;
    move-result-object v0
    return-object v0
'''+s[end:]
start=s.index('    # getter for: Lblackrussia/online/Downloader;->loadingInfo:',s.index('    :cond_14',s.index('.method protected onPostExecute(Ljava/lang/Integer;)V')))
end=s.index('    :goto_4f',start)
s=s[:start]+f'''    invoke-static {{v0, p0}}, {helper}->showFailure(Landroid/app/Activity;Landroid/os/AsyncTask;)V
    return-void

'''+s[end:]
p.write_text(s)
