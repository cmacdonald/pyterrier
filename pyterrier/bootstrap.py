import deprecation

from . import mavenresolver

stdout_ref = None
stderr_ref = None
TERRIER_PKG = "org.terrier"

@deprecation.deprecated(deprecated_in="0.1.3",
                        # remove_id="",
                        details="Use the logging(level) function instead")
def setup_logging(level):
    logging(level,True)

def logging(level, use_jpype):
    if use_jpype:
        from jpype import JClass
        JClass("org.terrier.python.PTUtils").setLogLevel(level, None)
    else:
        from jnius import autoclass
        autoclass("org.terrier.python.PTUtils").setLogLevel(level, None)
# make an alias
_logging = logging


def setup_java_bridge(jpype):

    def _iterableposting_next(iterable_posting):
        ''' dunder method for iterating IterablePosting '''
        nextid = iterable_posting.next()
        # 2147483647 is IP.EOL. fix this once static fields can be read from instances.
        if 2147483647 == nextid:
            raise StopIteration()
        return iterable_posting

    def _lexicon_getitem(lexicon, term):
        ''' dunder method for accessing Lexicon '''
        rtr = lexicon.getLexiconEntry(term)
        if rtr is None:
            raise KeyError()
        return rtr

    if jpype:
        from jpype import _jcustomizer

        @_jcustomizer.JImplementationFor('org.terrier.structures.postings.IterablePosting')
        class _JIterablePosting(object):
            def __iter__(self):
                return self

            def __next__(self):
                return _iterableposting_next(self)

        @_jcustomizer.JImplementationFor('org.terrier.structures.Lexicon')
        class _JLexicon:
            def __getitem__(self, term):
                return _lexicon_getitem(self, term)

            def __contains__(self, term):
                return self.getLexiconEntry(term) is not None

            def __len__(self):
                return self.numberOfEntries()
    else:
        from jnius import protocol_map

        protocol_map["org.terrier.structures.postings.IterablePosting"] = {
            '__iter__': lambda self: self,
            '__next__': lambda self: _iterableposting_next(self)
        }

        protocol_map["org.terrier.structures.Lexicon"] = {
            '__getitem__': _lexicon_getitem,
            '__contains__': lambda self, term: self.getLexiconEntry(term) is not None,
            '__len__': lambda self: self.numberOfEntries()
        }


def setup_terrier(file_path, terrier_version=None, helper_version=None, boot_packages=[]):
    """
    Download Terrier's jar file for the given version at the given file_path
    Called by pt.init()

    Args:
        file_path(str): Where to download
        terrier_version(str): Which version of Terrier - None is latest release; "snapshot" uses Jitpack to download a build of the current Github 5.x branch.
        helper_version(str): Which version of the helper - None is latest
    """
    # If version is not specified, find newest and download it
    if terrier_version is None:
        terrier_version = mavenresolver.latest_version_num(TERRIER_PKG, "terrier-assemblies")
    else:
        terrier_version = str(terrier_version) # just in case its a float
    # obtain the fat jar from Maven
    # "snapshot" means use Jitpack.io to get a build of the current
    # 5.x branch from Github - see https://jitpack.io/#terrier-org/terrier-core/5.x-SNAPSHOT
    if terrier_version == "snapshot":
        trJar = mavenresolver.downloadfile("com.github.terrier-org.terrier-core", "terrier-assemblies", "5.x-SNAPSHOT", file_path, "jar-with-dependencies", force_download=True)
    else:
        trJar = mavenresolver.downloadfile(TERRIER_PKG, "terrier-assemblies", terrier_version, file_path, "jar-with-dependencies")

    # now the helper classes
    if helper_version is None:
        helper_version = mavenresolver.latest_version_num(TERRIER_PKG, "terrier-python-helper")
    else:
        helper_version = str(helper_version) # just in case its a float
    helperJar = mavenresolver.downloadfile(TERRIER_PKG, "terrier-python-helper", helper_version, file_path, "jar")

    classpath=[trJar, helperJar]
    for b in boot_packages:
        parts = b.split(":")
        if len(parts)  < 2 or len(parts) > 4:
            raise ValueError("Invalid format for package %s" % b)
        group = parts[0]
        pkg = parts[1]
        filetype = "jar"
        version = None
        if len(parts) > 2:
            version = parts[2]
            if len(parts) > 3:
                filetype = parts[3]
        #print((group, pkg, filetype, version))
        filename = mavenresolver.downloadfile(group, pkg, version, file_path, filetype)
        classpath.append(filename)

    return classpath

def is_binary(f):
    import io
    return isinstance(f, (io.RawIOBase, io.BufferedIOBase))

def redirect_stdouterr(jpype):

    def _close(output_streamable):
        output_streamable.pystream.close()

    def _flush(output_streamable):
        output_streamable.pystream.flush()

    def _writeByteArray(output_streamable, byteArray):
        # TODO probably this could be faster.
        for c in byteArray:
            output_streamable.writeChar(c)

    def _writeByteArrayIntInt(output_streamable, byteArray, offset, length):
        # TODO probably this could be faster.
        for i in range(offset, offset + length):
            output_streamable.writeChar(byteArray[i])

    def _writeChar(output_streamable, chara):
        if output_streamable.binary:
            return output_streamable.pystream.write(bytes([chara]))
        return output_streamable.pystream.write(chr(chara))

    # TODO: encodings may be a probem here
    if jpype:
        from jpype import JClass, JOverride, JImplements

        @JImplements("org.terrier.python.OutputStreamable")
        class MyOut:
            def __init__(self, pystream):
                self.pystream = pystream
                self.binary = is_binary(pystream)

            @JOverride()
            def close(self):
                _close(self)

            @JOverride()
            def flush(self):
                _flush(self)

            @JOverride()
            def write(self, *args):
                # Must implement a method dispatch for overloaded method
                if len(args) == 1:
                    if isinstance(args[0], int):
                        return _writeChar(self, *args)
                    else:
                        _writeByteArray(self, *args)
                elif len(args) == 3:
                    _writeByteArrayIntInt(self, *args)
    else:
        from jnius import autoclass, PythonJavaClass, java_method

        class MyOut(PythonJavaClass):
            __javainterfaces__ = ['org.terrier.python.OutputStreamable']

            def __init__(self, pystream):
                super(MyOut, self).__init__()
                self.pystream = pystream
                self.binary = is_binary(pystream)

            @java_method('()V')
            def close(self):
                _close(self)

            @java_method('()V')
            def flush(self):
                _flush(self)

            @java_method('([B)V', name='write')
            def writeByteArray(self, byteArray):
                _writeByteArray(self, byteArray)

            @java_method('([BII)V', name='write')
            def writeByteArrayIntInt(self, byteArray, offset, length):
                _writeByteArrayIntInt(self, byteArray, offset, length)

            @java_method('(I)V', name='write')
            def writeChar(self, chara):
                _writeChar(chara)

    # we need to hold lifetime references to stdout_ref/stderr_ref, to ensure
    # they arent GCd. This prevents a crash when Java callsback to  GCd py obj

    global stdout_ref
    global stderr_ref
    import sys
    stdout_ref = MyOut(sys.stdout)
    stderr_ref = MyOut(sys.stderr)

    if jpype:
        jls = JClass("java.lang.System")
        jls.setOut(
            JClass('java.io.PrintStream')(JClass('org.terrier.python.ProxyableOutputStream')(stdout_ref)))
        jls.setErr(
            JClass('java.io.PrintStream')(JClass('org.terrier.python.ProxyableOutputStream')(stderr_ref)))
    else:
        jls = autoclass("java.lang.System")
        jls.setOut(
            autoclass('java.io.PrintStream')(
                autoclass('org.terrier.python.ProxyableOutputStream')(stdout_ref),
                signature="(Ljava/io/OutputStream;)V"))
        jls.setErr(
            autoclass('java.io.PrintStream')(
                autoclass('org.terrier.python.ProxyableOutputStream')(stderr_ref),
                signature="(Ljava/io/OutputStream;)V"))

