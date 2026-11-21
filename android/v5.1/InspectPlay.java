import java.io.*;
import java.util.*;
import java.util.zip.*;
import org.jf.dexlib2.*;
import org.jf.dexlib2.dexbacked.DexBackedDexFile;
import org.jf.dexlib2.iface.*;
import org.jf.dexlib2.iface.instruction.*;
import org.jf.dexlib2.iface.reference.*;
public class InspectPlay {
    public static void main(String[] args) throws Exception {
        Set<String> callers=new HashSet<>(), clicks=new HashSet<>();
        String target="Lblackrussia/online/Downloader;";
        try (ZipFile zip=new ZipFile(args[0])) {
            for (ZipEntry entry: Collections.list(zip.entries())) {
                if (!entry.getName().matches("classes[0-9]*\\.dex")) continue;
                try (BufferedInputStream input=new BufferedInputStream(zip.getInputStream(entry))) {
                    for (ClassDef c:DexBackedDexFile.fromInputStream(Opcodes.getDefault(),input).getClasses()) {
                        if(c.getType().startsWith("Lblackrussia/online/Downloader"))continue;
                        for(Method m:c.getMethods()) {
                            if(m.getImplementation()==null)continue;
                            for(Instruction op:m.getImplementation().getInstructions()) {
                                if(!(op instanceof ReferenceInstruction))continue;
                                Reference ref=((ReferenceInstruction)op).getReference();
                                if(ref instanceof TypeReference && ((TypeReference)ref).getType().equals(target))
                                    callers.add(c.getType()+"->"+m.getName());
                                if(ref instanceof MethodReference) {
                                    MethodReference method=(MethodReference)ref;
                                    if(method.getDefiningClass().equals("Lblackrussia/online/activities/MainActivity;") && method.getName().equals("onClickPlay"))
                                        clicks.add(c.getType()+"->"+m.getName());
                                }
                            }
                        }
                    }
                }
            }
        }
        System.out.println("Stock downloader entry points "+callers);
        System.out.println("Play callback invoked from "+clicks);
        if (!clicks.equals(Collections.singleton("Lblackrussia/online/activities/MainActivity$4$1;->run"))) throw new AssertionError(clicks);
        if(!callers.equals(Collections.singleton("Lblackrussia/online/activities/MainActivity;->onClickPlay")))throw new AssertionError(callers);
    }
}
