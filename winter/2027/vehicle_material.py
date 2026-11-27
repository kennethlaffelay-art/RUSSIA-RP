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
    # Preserve signed horizontal direction across the hood and the doors.
    line('Out_Tex1 = vec2(length(reflVector.xy), (reflVector.z * 0.5) + 0.25);',
         'vE=vec3(.5+.49*r.x,.5-.49*r.z,F);')
    line('Out_Refl = reflVector;', 'Out_Refl=vec4(r,F);')
    line('fcolor.xyz = mix(fcolor.xyz, texture2D(EnvMap, Out_Tex1).xyz, EnvMapCoefficient);',
         'fcolor.rgb=mix(fcolor.rgb,texture2D(EnvMap,vE.xy).rgb,EnvMapCoefficient*vE.z);')
    # Project onto the environment disk without normalizing a zero XY vector at its poles.
    line('vec2 ReflPos = normalize(Out_Refl.xy) * (Out_Refl.z * 0.5 + 0.5);',
         'vec2 ReflPos=Out_Refl.xy*inversesqrt(max(2.-2.*Out_Refl.z,.001));')
    # Glass and cutouts retain the opacity authored by the model. On opaque panels,
    # compress the directional highlight so its core does not clip too early.
    line('fcolor.w += ReflTexture.b * 0.125;', '')
    line('Out_Spec = specAmt * DirLightDiffuseColor;', 'Out_Spec=DirLightDiffuseColor*s/(1.+s);')
    old_mix = 'fcolor.xyz = mix(fcolor.xyz,{}ReflTexture.xyz, EnvMapCoefficient);'
    if library == 'libGame.so':
        line('lowp vec4 ReflTexture =  texture2D(EnvMap, ReflPos);',
             'lowp vec4 env=texture2D(EnvMap,ReflPos);')
        line(old_mix.format(''), 'fcolor.rgb=mix(fcolor.rgb,env.rgb,EnvMapCoefficient*Out_Refl.w);')
        for scale in ('EnvMapCoefficient * 2.0', '0.125'):
            line('float specAmt = max(pow(dot(reflVector, DirLightDirection), %.1f), 0.0) * '+scale+';',
                 'float s=pow(max(dot(r,DirLightDirection),0.),%.1f)*'+scale+';')
    else:
        line('lowp vec4 ReflTexture;', 'lowp vec4 env;')
        line('ReflTexture = texture2D(EnvMap, ReflPos);', 'env=texture2D(EnvMap,ReflPos);')
        line(old_mix.format(' '), 'fcolor.rgb=mix(fcolor.rgb,env.rgb,EnvMapCoefficient*Out_Refl.w);')
        line('fcolor.xyz = mix(fcolor.xyz, ReflTexture.xyz, reflectAmt);',
             'fcolor.rgb=mix(fcolor.rgb,env.rgb,reflectAmt);')
        line('float specAmt = max(pow(dot(reflVector, DirLightDirection), ',
             'float s=max(pow(max(dot(r,DirLightDirection),0.),')
    return data
