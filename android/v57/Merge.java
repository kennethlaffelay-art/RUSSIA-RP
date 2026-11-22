import java.io.File;
import java.util.HashMap;
import org.jf.dexlib2.DexFileFactory;
import org.jf.dexlib2.Opcodes;
import org.jf.dexlib2.iface.ClassDef;
import org.jf.dexlib2.iface.DexFile;
import org.jf.dexlib2.writer.io.FileDataStore;
import org.jf.dexlib2.writer.pool.DexPool;

public class Merge {
    public static void main(String[] paths) throws Exception {
        DexFile base = DexFileFactory.loadDexFile(new File(paths[0]), null);
        Opcodes ops = base.getOpcodes();
        DexFile changes = DexFileFactory.loadDexFile(new File(paths[1]), ops);
        HashMap<String,ClassDef> replace = new HashMap<>();
        for (ClassDef c : changes.getClasses()) replace.put(c.getType(), c);
        if (replace.size() != 2) throw new IllegalStateException();
        DexPool out = new DexPool(ops);
        for (ClassDef cls : base.getClasses()) {
            ClassDef replacement = replace.remove(cls.getType());
            out.internClass(replacement == null ? cls : replacement);
        }
        if (!replace.isEmpty()) throw new IllegalStateException();
        FileDataStore store = new FileDataStore(new File(paths[2]));
        try { out.writeTo(store); } finally { store.close(); }
    }
}
