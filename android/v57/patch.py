"""Apply the UI registration and render-surface lifecycle changes to the v5.6 smali."""
from pathlib import Path
import re, sys
root=Path(sys.argv[1])
nv = 'Lcom/nvidia/devtech/NvEventQueueActivity;'
egl = 'Ljavax/microedition/khronos/egl/'
T = lambda name: egl + name + ';'
gui_path = root/'com/wn/blackrussia/game/GUIManager.smali'
ui = gui_path.read_text()
start = ui.index('    const/4 v1, 0x3',ui.index('.method static constructor'))
end = ui.index('    .line 31',start)
assert 'ui/WnPopup;' in ui[start:end]
new_ui = (ui[:start]+ui[end:]).replace('const/4 v0, 0x4','const/4 v0, 0x3',1)

path = root/'com/nvidia/devtech/NvEventQueueActivity.smali'
s = path.read_text()
def once(old, new):
    global s
    assert s.count(old)==1, old
    s=s.replace(old,new,1)

# The last GLES2 attempt is a fallback for hardware exposing only RGB565.
once('const/4 v2, 0x5\n\n    .line 820','const/16 v2, 0x8\n\n    .line 820')
once('const/4 v3, 0x6\n\n    .line 822','move v3, v2\n\n    .line 822')
once('    .line 680\n',f'''    const/4 v4, 0x5
    iput v4, p0, {nv}->redSize:I
    iput v4, p0, {nv}->blueSize:I
    const/4 v4, 0x6
    iput v4, p0, {nv}->greenSize:I
    .line 680
''')
# Keep SurfaceHolder's default opaque format. EGL picks a supported window visual.
once('invoke-interface {v1, v3}, Landroid/view/SurfaceHolder;->setType(I)V','nop')
once('    .line 849\n',f'''    const/4 v2, 0x0
    iput-object v2, v0, {nv}->eglConfig:{T('EGLConfig')}
    iput-object v2, v0, {nv}->configAttrs:[I
    .line 849
''')
once('    .line 965\n',f'''    if-eqz v1, :context_failed
    if-ne v1, v4, :context_ok
    :context_failed
    const/4 v1, 0x0
    iput-object v1, v0, {nv}->eglContext:{T('EGLContext')}
    return v16
    :context_ok
    .line 965
''')
once('    .line 978\n','''    if-eqz p1, :unavailable
    invoke-interface {p1}, Landroid/view/SurfaceHolder;->getSurface()Landroid/view/Surface;
    move-result-object v0
    if-eqz v0, :unavailable
    invoke-virtual {v0}, Landroid/view/Surface;->isValid()Z
    move-result v0
    if-eqz v0, :unavailable
    .line 978
''')
call='    invoke-interface {v0, v1, v2, p1, v3}, '+T('EGL10')+'->eglCreateWindowSurface'
once(call,'    :surface_try\n'+call)
once('    .line 979\n',f'''    :surface_end
    .catch Ljava/lang/IllegalArgumentException; {{:surface_try .. :surface_end}} :bad_window
    if-eqz p1, :unavailable
    sget-object v0, {T('EGL10')}->EGL_NO_SURFACE:{T('EGLSurface')}
    if-eq p1, v0, :unavailable
    .line 979
''')
for line in (982,984):
    token=('    const/4 v2, 0x0\n\n' if line==982 else '') + f'    .line {line}\n'
    once(token,'    move-result v6\n    if-eqz v6, :discard_surface\n'+token)
for reg,field,line in [('v3','surfaceWidth',983),('v1','surfaceHeight',985)]:
    token=f'    iput {reg}, p0, {nv}->{field}:I\n\n    .line {line}'
    once(token,f'    if-lez {reg}, :discard_surface\n'+token)
once('    .line 989\n','    move-result v1\n    if-eqz v1, :discard_surface\n    .line 989\n')
once('    .line 991\n','    move-result v1\n    if-eqz v1, :discard_surface\n    .line 991\n')
once('    return p1\n.end method\n\n.method public native customMultiTouchEvent',f'''    return p1
    :bad_window
    move-exception v0
    goto :unavailable
    :discard_surface
    invoke-virtual {{p0}}, {nv}->destroyEGLSurface()V
    :unavailable
    const/4 v0, 0x0
    iput-object v0, p0, {nv}->eglSurface:{T('EGLSurface')}
    iput-boolean v0, p0, {nv}->viewIsActive:Z
    iput v0, p0, {nv}->surfaceWidth:I
    iput v0, p0, {nv}->surfaceHeight:I
    return v0
.end method

.method public native customMultiTouchEvent''')
once('    .line 690\n','    move-result p1\n    if-eqz p1, :cond_96\n    .line 690\n')
path.write_text(s)
gui_path.write_text(new_ui)
