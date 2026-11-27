"""Add angle-dependent clear-coat reflection to the existing mobile material shaders."""


def vehicle_material(data, library):
    # Both shader builders concatenate some literals with explicit byte counts.
    # Keep the storage address, the emitted length, and any final newline intact.
    def line(old, new, newline=False):
        nonlocal data
        tail = b'\n' if newline else b''
        old = old.encode()
        new = new.encode()
        if len(new) > len(old):
            raise ValueError(f'GLSL entry outgrew its slot: {new!r}')
        before = b'\0' + old + tail + b'\0'
        after = b'\0' + new.ljust(len(old)) + tail + b'\0'
        if data.count(before) != 1:
            raise ValueError(f'Unexpected {library} shader template: {old!r}')
        data = data.replace(before, after)

    # F carries the surface response: 30% of the material's reflection at
    # normal incidence and the original authored strength at grazing incidence.
    line('vec3 reflVector = normalize(WorldPos.xyz - CameraPosition.xyz);',
         'vec3 r=normalize(WorldPos.xyz-CameraPosition.xyz);float F;')
    line('reflVector = reflVector - 2.0 * dot(reflVector, WorldNormal) * WorldNormal;',
         'F=1.-min(abs(dot(r,WorldNormal)),1.);F=.3+.7*F*F;r=reflect(r,WorldNormal);')
    for newline in ([False,True] if library == 'libmultiplayer.so' else [False]):
        line('varying mediump vec2 Out_Tex1;', 'varying mediump vec3 vE;', newline)
        line('varying mediump vec3 Out_Refl;', 'varying mediump vec4 Out_Refl;', newline)
    line('Out_Tex1 = vec2(length(reflVector.xy), (reflVector.z * 0.5) + 0.25);',
         'vE=vec3(length(r.xy),r.z*.5+.25,F);')
    line('Out_Refl = reflVector;', 'Out_Refl=vec4(r,F);')
    line('fcolor.xyz = mix(fcolor.xyz, texture2D(EnvMap, Out_Tex1).xyz, EnvMapCoefficient);',
         'fcolor.rgb=mix(fcolor.rgb,texture2D(EnvMap,vE.xy).rgb,EnvMapCoefficient*vE.z);')
    line('fcolor.w += ReflTexture.b * 0.125;', 'fcolor.w+=env.b*.08*Out_Refl.w;')
    old_mix = 'fcolor.xyz = mix(fcolor.xyz,{}ReflTexture.xyz, EnvMapCoefficient);'
    if library == 'libGame.so':
        line('lowp vec4 ReflTexture =  texture2D(EnvMap, ReflPos);',
             'lowp vec4 env=texture2D(EnvMap,ReflPos);')
        line(old_mix.format(''), 'fcolor.rgb=mix(fcolor.rgb,env.rgb,EnvMapCoefficient*Out_Refl.w);')
        for scale in ('EnvMapCoefficient * 2.0', '0.125'):
            line('float specAmt = max(pow(dot(reflVector, DirLightDirection), %.1f), 0.0) * '+scale+';',
                 'float specAmt=pow(max(dot(r,DirLightDirection),0.),%.1f)*'+scale+';')
    else:
        line('lowp vec4 ReflTexture;', 'lowp vec4 env;')
        line('ReflTexture = texture2D(EnvMap, ReflPos);', 'env=texture2D(EnvMap,ReflPos);')
        line(old_mix.format(' '), 'fcolor.rgb=mix(fcolor.rgb,env.rgb,EnvMapCoefficient*Out_Refl.w);')
        line('fcolor.xyz = mix(fcolor.xyz, ReflTexture.xyz, reflectAmt);',
             'fcolor.rgb=mix(fcolor.rgb,env.rgb,reflectAmt);')
        line('float specAmt = max(pow(dot(reflVector, DirLightDirection), ',
             'float specAmt=max(pow(max(dot(r,DirLightDirection),0.),')
    return data
