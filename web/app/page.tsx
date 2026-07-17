export default function Home() {
  return (
    <main style={{ padding: '4rem', fontFamily: 'monospace', background: '#0a0a0a', color: '#0f0', minHeight: '100vh' }}>
      <h1>SOLVENS CORE: AI Operating System</h1>
      <h2>✅ ARM64 Android Verified</h2>
      <p><b>Device:</b> Huawei Nova 5T, Kirin 980, 6GB RAM</p>
      <p><b>Test:</b> 512x512 Strassen multiply</p>
      <p><b>Result:</b> Diff 4.14e-12 vs NumPy ✓ PASS</p>
      <br/>
      <p><b>Architecture:</b> Lexer → Parser → AST → Optimizer → Codegen</p>
      <p><b>FAQ:</b> ¿Es wrapper de NumPy? NO. 0 imports.</p>
      <br/>
      <a href="https://github.com/SolvensAmoris/solvens-core" style={{ color: '#0ff' }}>GitHub Repository</a>
      <br/><br/>
      <a href="https://pypi.org/project/cosmos-compiler/" style={{ color: '#0ff' }}>PyPI: cosmos-compiler</a>
      <br/>
      <a href="https://pypi.org/project/cosmos-language/" style={{ color: '#0ff' }}>PyPI: cosmos-language</a>
      <br/><br/>
      <p>Hecho desde cero en Empalme, Sonora, México 🌵</p>
      <p>Author: Luis Alberto Burciaga Miker</p>
    </main>
  )
}
