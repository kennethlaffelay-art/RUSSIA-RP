"""Add a separate inventory window, retaining the client's cached ordinary dialog."""
from pathlib import Path

def patch(decoded):
    root=decoded/'smali/com/wn/blackrussia'
    cfg=root/'BuildConfig.smali'
    s=cfg.read_text()
    assert '0x2b' in s and '1.7.19' in s
    cfg.write_text(s.replace('VERSION_CODE:I = 0x2b','VERSION_CODE:I = 0x2c').replace('"1.7.19"','"1.7.20"'))
    ui=root/'game/ui'
    menu=ui/'GUIDialogMenu.smali'
    s=menu.read_text()
    assert s.count('"/inv"')==1
    menu.write_text(s.replace('"/inv"','"/items"'))
    dialog=ui/'BrDialogWindow.smali'
    s=dialog.read_text()
    owner='Lcom/wn/blackrussia/game/ui/BrDialogWindow;'
    window='Landroid/widget/PopupWindow;'
    bag='Lcom/russiarp/inventory/BagWindow;'
    field=owner+'->mInventoryWindow:'+window
    s=s.replace('# instance fields','# instance fields\n.field private mInventoryWindow:'+window+'\n',1)
    def inject(signature,code,locals=1):
        nonlocal s
        head='.method public '+signature+'\n    .locals '+str(locals)+'\n'
        assert s.count(head)==1,signature
        s=s.replace(head,head+code+'\n')
    clear=f'''
    iget-object v0, p0, {field}
    invoke-static {{v0}}, {bag}->replace({window})V
    const/4 v0, 0x0
    iput-object v0, p0, {field}
'''
    inject('show(IILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V',clear+f'''
    iget-boolean v0, p0, {owner}->mIsShow:Z
    if-nez v0, :regular
    iget-object v0, p0, {owner}->activity:Landroid/app/Activity;
    invoke-static {{v0, p1, p3, p4}}, {bag}->open(Landroid/app/Activity;ILjava/lang/String;Ljava/lang/String;){window}
    move-result-object v0
    if-eqz v0, :regular
    iput-object v0, p0, {field}
    return-void
    :regular
''')
    inject('getVis()Z',f'''
    iget-object v0, p0, {field}
    if-eqz v0, :regular
    invoke-virtual {{v0}}, {window}->isShowing()Z
    move-result v0
    if-eqz v0, :regular
    return v0
    :regular
''')
    inject('tempToggle(Z)V',f'''
    iget-object v0, p0, {field}
    invoke-static {{v0, p1}}, {bag}->setContentVisible({window}Z)Z
    move-result v0
    if-eqz v0, :regular
    iput-boolean p1, p0, {owner}->m_bIsTempToggled:Z
    return-void
    :regular
''')
    inject('close()V',clear)
    dialog.write_text(s)
