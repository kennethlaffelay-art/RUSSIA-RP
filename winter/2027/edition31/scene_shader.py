def scene_shader(raw, library):
    # Mobile shader builders retain literal lengths. Preserve both the allocation
    # and the emitted source length, including existing terminators.
    def replace(old,new,embedded=False):
        nonlocal raw
        old,new = old.encode(),new.encode()
        left,right = (b'\n\t',b'\n') if embedded else (b'\0',b'\0')
        if len(new)>len(old) or raw.count(left+old+right)!=1:
            raise ValueError(f'Unexpected {library} scene shader: {old}')
        raw = raw.replace(left+old+right,left+new.ljust(len(old))+right)

    replace('fcolor.xyz = mix(fcolor.xyz, FogColor, Out_FogAmt);',
            'fcolor.rgb=mix(fcolor.rgb,FogColor,Out_FogAmt*.92);')
    if library=='libGame.so':
        replace('Out_LightingColor += max(dot(DirLightDirection, WorldNormal), 0.0) * DirLightDiffuseColor;',
                'Out_LightingColor+=max(.2+.8*dot(DirLightDirection,WorldNormal),0.)*DirLightDiffuseColor;')
        replace('Out_LightingColor += (max(dot(DirLightDirection, WorldNormal), 0.0) + max(dot(DirBackLightDirection, WorldNormal), 0.0)) * DirLightDiffuseColor;',
                'Out_LightingColor+=(max(.2+.8*dot(DirLightDirection,WorldNormal),0.)+.9*max(dot(DirBackLightDirection,WorldNormal),0.))*DirLightDiffuseColor;')
    else:
        replace('Out_FogAmt = fogDist * pow(fogHeight, 1.6);',
                'Out_FogAmt=fogDist*pow(fogHeight,1.38);',embedded=True)
    return raw
