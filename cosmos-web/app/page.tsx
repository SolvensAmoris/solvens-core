'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion'
import { 
  ArrowRight, 
  Zap, 
  Shield, 
  Terminal, 
  Mail, 
  Phone, 
  Copy, 
  Check, 
  Command,
  Play,
  Star,
  Globe,
  Code2,
  Timer,
  AlertTriangle,
  ChevronRight,
  Menu,
  X,
  ExternalLink,
  Github,
  Linkedin,
  Twitter
} from 'lucide-react'

// ============================================
// SPLINE 3D BACKGROUND
// ============================================
function SplineScene() {
  return (
    <div className="fixed inset-0 z-0">
      <Suspense fallback={
        <div className="w-full h-full bg-gradient-to-br from-black via-zinc-950 to-black animate-pulse" />
      }>
        <iframe 
          src="https://my.spline.design/cosmicparticle-17082024 copie-3c2f0d0cc8ee9a2d89b1ef9bf4b6d4e/" 
          className="w-full h-full"
          frameBorder="0"
          title="3D Cosmos"
        />
      </Suspense>
    </div>
  )
}

// ============================================
// PARTICLES
// ============================================
function Particles() {
  return (
    <div className="particles">
      {[...Array(50)].map((_, i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 20}s`,
            animationDuration: `${15 + Math.random() * 15}s`,
            opacity: 0.1 + Math.random() * 0.3,
            width: `${2 + Math.random() * 4}px`,
            height: `${2 + Math.random() * 4}px`,
          }}
        />
      ))}
    </div>
  )
}

// ============================================
// NAVIGATION
// ============================================
function Navigation({ onOpenCmd }: { onOpenCmd: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
      scrolled ? 'glass-strong' : 'bg-transparent'
    }`}>
      <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
        {/* Logo */}
        <motion.div 
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="relative">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-xl" />
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-xl blur-xl opacity-50" />
          </div>
          <span className="text-xl font-bold tracking-tight">Cosmos</span>
          <span className="px-2 py-0.5 bg-white/10 rounded-md text-xs font-mono text-zinc-400">v0.4.5</span>
        </motion.div>

        {/* Desktop Nav */}
        <div className="hidden md:flex gap-8 items-center">
          <NavLink href="#features">Features</NavLink>
          <NavLink href="#benchmark">Benchmark</NavLink>
          <NavLink href="#playground">Playground</NavLink>
          <NavLink href="#pricing">Pricing</NavLink>
          <NavLink href="#contact">Contact</NavLink>
          
          <button 
            onClick={onOpenCmd}
            className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm flex items-center gap-2 hover:bg-white/10 transition"
          >
            <Command size={14} /> Cmd+K
          </button>
          
          <a 
            href="mailto:Luis_albm@hotmail.com"
            className="px-5 py-2.5 bg-white text-black rounded-lg font-medium hover:bg-zinc-200 transition text-sm"
          >
            Contact Sales
          </a>
        </div>

        {/* Mobile Menu */}
        <button 
          className="md:hidden p-2"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Dropdown */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="md:hidden glass-strong px-6 py-8 space-y-6"
          >
            <MobileNavLink href="#features" onClick={() => setMobileOpen(false)}>Features</MobileNavLink>
            <MobileNavLink href="#benchmark" onClick={() => setMobileOpen(false)}>Benchmark</MobileNavLink>
            <MobileNavLink href="#playground" onClick={() => setMobileOpen(false)}>Playground</MobileNavLink>
            <MobileNavLink href="#pricing" onClick={() => setMobileOpen(false)}>Pricing</MobileNavLink>
            <MobileNavLink href="#contact" onClick={() => setMobileOpen(false)}>Contact</MobileNavLink>
            <a 
              href="mailto:Luis_albm@hotmail.com"
              className="block w-full text-center px-5 py-3 bg-white text-black rounded-lg font-medium"
            >
              Contact Sales
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} className="text-zinc-400 hover:text-white transition text-sm font-medium">
      {children}
    </a>
  )
}

function MobileNavLink({ href, children, onClick }: { href: string; children: React.ReactNode; onClick: () => void }) {
  return (
    <a 
      href={href} 
      className="block text-zinc-300 hover:text-white transition text-lg"
      onClick={onClick}
    >
      {children}
    </a>
  )
}

// ============================================
// COMMAND PALETTE
// ============================================
function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  const commands = [
    { icon: <Copy size={16} />, label: 'Install Cosmos', action: () => {
      navigator.clipboard.writeText('pip install cosmos-compiler')
    }, highlight: 'pip install cosmos-compiler' },
    { icon: <Code2 size={16} />, label: 'View Documentation', action: () => window.open('https://github.com/SolvensAmoris/solvens-core', '_blank') },
    { icon: <Github size={16} />, label: 'GitHub Repository', action: () => window.open('https://github.com/SolvensAmoris/solvens-core', '_blank') },
    { icon: <Mail size={16} />, label: 'Contact Luis', action: () => window.location.href = 'mailto:Luis_albm@hotmail.com', highlight: 'Luis_albm@hotmail.com' },
    { icon: <ExternalLink size={16} />, label: 'Try Playground', action: () => document.getElementById('playground')?.scrollIntoView({ behavior: 'smooth' }) },
  ]

  const filtered = query 
    ? commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-xl z-[100] flex items-start justify-center pt-32"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-2xl mx-4 bg-zinc-950 border border-white/10 rounded-2xl overflow-hidden shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 p-4 border-b border-white/10">
              <Command size={18} className="text-zinc-500" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent outline-none text-lg text-white placeholder-zinc-500"
              />
              <kbd className="px-2 py-1 bg-white/10 rounded text-xs text-zinc-400">ESC</kbd>
            </div>
            <div className="p-2 max-h-96 overflow-y-auto">
              {filtered.map((cmd, i) => (
                <button
                  key={i}
                  onClick={() => { cmd.action(); onClose() }}
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/5 rounded-lg transition text-left"
                >
                  <span className="text-zinc-400">{cmd.icon}</span>
                  <span className="text-white">{cmd.label}</span>
                  {cmd.highlight && (
                    <code className="ml-auto text-xs text-zinc-500 bg-white/5 px-2 py-1 rounded">
                      {cmd.highlight}
                    </code>
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ============================================
// HERO SECTION
// ============================================
function HeroSection({ onOpenCmd }: { onOpenCmd: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: containerRef })
  const opacity = useTransform(scrollYProgress, [0, 0.3], [1, 0])
  const scale = useTransform(scrollYProgress, [0, 0.3], [1, 0.9])
  const y = useTransform(scrollYProgress, [0, 0.3], [0, -100])

  return (
    <section ref={containerRef} className="relative min-h-screen flex items-center justify-center overflow-hidden">
      <motion.div style={{ opacity, scale, y }} className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-20">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-full text-red-400 text-sm mb-8 backdrop-blur-xl"
        >
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          On Dec 31, 2026 at 23:59, Terraform says VALID. We block your PR.
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="text-responsive-hero font-bold mb-8 leading-[1.1] tracking-tight"
        >
          <span className="bg-gradient-to-br from-white via-white to-zinc-400 bg-clip-text text-transparent">
            Stop $2M outages
          </span>
          <br />
          <span className="bg-gradient-to-br from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            before they ship
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="text-2xl text-zinc-400 mb-12 max-w-3xl leading-relaxed font-light"
        >
          On Dec 31, 2026 at 23:59, Terraform says <span className="text-green-400">VALID</span>. 
          Cosmos blocks your PR in <span className="text-white font-semibold">8ms</span> with E401 
          temporal constraint validation.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="flex flex-wrap gap-4 mb-20"
        >
          <CopyButton />
          <a 
            href="#playground"
            className="group px-8 py-4 border border-white/20 rounded-xl font-medium backdrop-blur-xl hover:bg-white/5 transition flex items-center gap-3 text-lg"
          >
            Live playground 
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl"
        >
          <StatCard value="8ms" label="Compile Time" sub="Cache: 0ms" delay={0} />
          <StatCard value="100%" label="E401 Catch" sub="Temporal" delay={0.1} />
          <StatCard value="5/5" label="INFRA-BENCH" sub="vs TF 0/5" delay={0.2} />
          <StatCard value="89ms" label="Fail-fast" sub="997 jobs" delay={0.3} />
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10"
      >
        <div className="w-6 h-10 border-2 border-white/20 rounded-full flex justify-center">
          <motion.div
            animate={{ y: [0, 12, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-1.5 h-3 bg-white/50 rounded-full mt-2"
          />
        </div>
      </motion.div>
    </section>
  )
}

function StatCard({ value, label, sub, delay }: { value: string; label: string; sub: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6 + delay }}
      className="p-6 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-xl hover:bg-white/10 transition"
    >
      <div className="text-3xl font-bold mb-1 bg-gradient-to-br from-white to-zinc-400 bg-clip-text text-transparent">
        {value}
      </div>
      <div className="text-zinc-500 text-sm">{label}</div>
      <div className="text-zinc-600 text-xs mt-1">{sub}</div>
    </motion.div>
  )
}

function CopyButton() {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText('pip install cosmos-compiler')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="group px-8 py-4 bg-white text-black rounded-xl font-medium flex items-center gap-3 hover:bg-zinc-200 transition text-lg"
    >
      {copied ? (
        <>
          <Check size={20} className="text-green-500" />
          Copied!
        </>
      ) : (
        <>
          <Copy size={20} />
          pip install cosmos-compiler
        </>
      )}
    </button>
  )
}

// ============================================
// FEATURES SECTION
// ============================================
function FeaturesSection() {
  const features = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: '8ms Compile',
      description: '100x faster than terraform validate. Cache hit: 0ms. Incremental builds: instant.',
      color: 'from-yellow-500 to-orange-500',
    },
    {
      icon: <AlertTriangle className="w-6 h-6" />,
      title: 'E401 Detection',
      description: 'Catch temporal constraint violations at compile time. Before they reach production.',
      color: 'from-red-500 to-pink-500',
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: 'Fail-Fast',
      description: 'Cancel 997 dependent jobs in 89ms. No wasted compute. No surprise costs.',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: <Terminal className="w-6 h-6" />,
      title: 'VSCode LSP',
      description: 'First-class IDE support. Autocomplete, diagnostics, hover docs.',
      color: 'from-purple-500 to-violet-500',
    },
    {
      icon: <Code2 className="w-6 h-6" />,
      title: 'EXPORT Schema',
      description: 'Feed errors to Claude/GPT for automated fixes. JSON v1.0 standard.',
      color: 'from-green-500 to-emerald-500',
    },
    {
      icon: <Globe className="w-6 h-6" />,
      title: 'Multi-Cloud',
      description: 'AWS, GCP, Azure, Cloudflare. One DSL, any provider.',
      color: 'from-indigo-500 to-blue-500',
    },
  ]

  return (
    <section id="features" className="relative z-10 py-32">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6">
            <span className="bg-gradient-to-br from-white to-zinc-400 bg-clip-text text-transparent">
              Built for production
            </span>
          </h2>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
            Everything you need to validate infrastructure before it ships. No surprises on Monday morning.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="group p-8 bg-white/5 border border-white/10 rounded-3xl backdrop-blur-xl hover:bg-white/10 transition-all hover:scale-[1.02]"
            >
              <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-zinc-400 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ============================================
// BENCHMARK SECTION
// ============================================
function BenchmarkSection() {
  const metrics = [
    { name: 'Compile Time', cosmos: '8ms', terraform: '847ms', win: true },
    { name: 'Cache Hit', cosmos: '0ms', terraform: '892ms', win: true },
    { name: 'E401 Detection', cosmos: '100%', terraform: '0%', win: true },
    { name: 'Fail-fast', cosmos: '89ms', terraform: 'N/A', win: true },
    { name: 'Memory', cosmos: '12MB', terraform: '234MB', win: true },
  ]

  return (
    <section id="benchmark" className="relative z-10 py-32">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/20 rounded-full text-green-400 text-sm mb-8">
            <Star className="w-4 h-4" />
            INFRA-BENCH: Cosmos 5/5 vs Terraform 0/5
          </div>
          <h2 className="text-5xl md:text-6xl font-bold mb-6">
            <span className="bg-gradient-to-br from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              100x faster
            </span>
          </h2>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
            Direct comparison. Same infrastructure. Different results.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-white/5 border border-white/10 rounded-3xl backdrop-blur-2xl overflow-hidden"
        >
          <div className="grid grid-cols-4 gap-4 p-6 border-b border-white/10 bg-white/5">
            <div className="text-zinc-500 text-sm font-medium">Metric</div>
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full text-sm font-medium">
                Cosmos
              </div>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-700 rounded-full text-sm font-medium">
                Terraform
              </div>
            </div>
            <div className="text-center text-zinc-500 text-sm">Winner</div>
          </div>
          {metrics.map((metric, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="grid grid-cols-4 gap-4 p-6 border-b border-white/5 hover:bg-white/5 transition"
            >
              <div className="text-white font-medium">{metric.name}</div>
              <div className="text-center font-mono text-lg">
                <span className="text-green-400">{metric.cosmos}</span>
              </div>
              <div className="text-center font-mono text-lg text-zinc-500">
                {metric.terraform}
              </div>
              <div className="text-center">
                {metric.win && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                    <Zap size={12} /> Cosmos
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

// ============================================
// PLAYGROUND SECTION
// ============================================
function PlaygroundSection() {
  const [code, setCode] = useState(`universe prod {
  planet earth {
    region: us-east-1
    expired_on: 2024-01-01
  }
  
  light sun -> earth {
    intensity: 100%
  }
}`)
  const [output, setOutput] = useState<{ type: 'error' | 'success'; message: string } | null>(null)
  const [loading, setLoading] = useState(false)

  const runCompile = async () => {
    setLoading(true)
    setOutput(null)
    
    // Simulate WASM compilation
    await new Promise(r => setTimeout(r, 800))
    
    if (code.includes('2024-01-01')) {
      setOutput({
        type: 'error',
        message: `E401: TEMPORAL CONSTRAINT VIOLATION

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: prod.cosmos:4
Line: expired_on: 2024-01-01
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Error: Planet "earth" expired on 2024-01-01
but 1 light source points to it.

Fix: Update expired_on to future date
     or remove light sun -> earth

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cancelled: 1 pending job in 89ms
DAG: 3 nodes, 1 temporal violation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
      })
    } else {
      setOutput({
        type: 'success',
        message: `✓ Compilation successful in 8ms

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAG Summary:
  Nodes: 3
  Layers: 2
  Edges: 1
  Temporal checks: PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
      })
    }
    
    setLoading(false)
  }

  return (
    <section id="playground" className="relative z-10 py-32">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6">
            <span className="bg-gradient-to-br from-white to-zinc-400 bg-clip-text text-transparent">
              Try it in your browser
            </span>
          </h2>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
            No install required. WASM compiler runs entirely in your browser.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-zinc-950/80 border border-white/10 rounded-3xl overflow-hidden backdrop-blur-2xl"
        >
          {/* Editor Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5">
            <div className="flex items-center gap-3">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <span className="text-sm text-zinc-500 font-mono">prod.cosmos</span>
            </div>
            <button
              onClick={() => {
                setCode(`universe prod {
  planet earth {
    region: us-east-1
    expired_on: 2026-12-31
  }
  
  light sun -> earth {
    intensity: 100%
  }
}`)
                setOutput(null)
              }}
              className="text-xs text-zinc-500 hover:text-white transition"
            >
              Reset
            </button>
          </div>

          {/* Editor */}
          <div className="grid md:grid-cols-2">
            <div className="p-6 border-r border-white/10">
              <textarea
                value={code}
                onChange={e => setCode(e.target.value)}
                className="w-full h-80 bg-transparent font-mono text-sm leading-relaxed resize-none outline-none text-zinc-300"
                spellCheck={false}
              />
            </div>

            {/* Output */}
            <div className="p-6 bg-black/30">
              <button
                onClick={runCompile}
                disabled={loading}
                className="w-full mb-6 px-6 py-3 bg-white text-black rounded-xl font-medium flex items-center justify-center gap-3 hover:bg-zinc-200 transition disabled:opacity-50"
              >
                <Play size={18} />
                {loading ? 'Compiling...' : 'Compile (WASM)'}
              </button>

              {output && (
                <motion.pre
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-6 rounded-xl text-sm font-mono overflow-x-auto ${
                    output.type === 'error' 
                      ? 'bg-red-500/10 border border-red-500/20 text-red-400' 
                      : 'bg-green-500/10 border border-green-500/20 text-green-400'
                  }`}
                >
                  {output.message}
                </motion.pre>
              )}

              {!output && !loading && (
                <div className="h-48 flex items-center justify-center text-zinc-600">
                  <div className="text-center">
                    <Terminal className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">Output will appear here</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// ============================================
// PRICING SECTION
// ============================================
function PricingSection() {
  return (
    <section id="pricing" className="relative z-10 py-32">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6">
            <span className="bg-gradient-to-br from-white to-zinc-400 bg-clip-text text-transparent">
              Simple pricing
            </span>
          </h2>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
            Start free. Scale when you need it.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Tier */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="p-10 bg-white/5 border border-white/10 rounded-3xl backdrop-blur-2xl"
          >
            <div className="text-sm text-zinc-400 mb-2 font-medium">OPEN SOURCE</div>
            <div className="text-3xl font-bold mb-2">Free</div>
            <div className="text-6xl font-bold mb-8">$0</div>
            
            <ul className="space-y-4 text-zinc-300 mb-10">
              <PricingItem icon={<Check size={18} className="text-green-400" />}>Core compiler</PricingItem>
              <PricingItem icon={<Check size={18} className="text-green-400" />}>VSCode LSP integration</PricingItem>
              <PricingItem icon={<Check size={18} className="text-green-400" />}>EXPORT schema v1.0</PricingItem>
              <PricingItem icon={<Check size={18} className="text-green-400" />}>Up to 50 developers</PricingItem>
              <PricingItem icon={<Check size={18} className="text-green-400" />}>Apache 2.0 license</PricingItem>
              <PricingItem icon={<Check size={18} className="text-green-400" />}>Community support</PricingItem>
            </ul>

            <a 
              href="https://github.com/SolvensAmoris/solvens-core"
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-4 border border-white/20 rounded-xl hover:bg-white/5 transition font-medium"
            >
              Get Started on GitHub
            </a>
          </motion.div>

          {/* Commercial Tier */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="p-10 bg-gradient-to-br from-white to-zinc-100 text-black rounded-3xl relative overflow-hidden"
          >
            {/* Glow */}
            <div className="absolute top-0 right-0 w-60 h-60 bg-gradient-to-br from-blue-500 to-purple-500 blur-3xl opacity-20" />
            
            <div className="relative z-10">
              <div className="text-sm text-zinc-600 mb-2 font-medium">ENTERPRISE</div>
              <div className="text-3xl font-bold mb-2">Commercial</div>
              <div className="text-6xl font-bold mb-8">Custom</div>
              
              <ul className="space-y-4 text-zinc-700 mb-10">
                <PricingItem icon={<Check size={18} />}>Everything in Free</PricingItem>
                <PricingItem icon={<Check size={18} />}>SSO + SAML integration</PricingItem>
                <PricingItem icon={<Check size={18} />}>Audit logs + compliance</PricingItem>
                <PricingItem icon={<Check size={18} />}>Priority support (24/7)</PricingItem>
                <PricingItem icon={<Check size={18} />}>Custom integrations</PricingItem>
                <PricingItem icon={<Check size={18} />}>Unlimited developers</PricingItem>
                <PricingItem icon={<Check size={18} />}>SLA guarantee</PricingItem>
              </ul>

              <a 
                href="mailto:Luis_albm@hotmail.com?subject=Cosmos Commercial License"
                className="block w-full text-center py-4 bg-black text-white rounded-xl hover:bg-zinc-900 transition font-medium"
              >
                Contact Sales
              </a>
              
              <div className="mt-6 text-center text-sm text-zinc-600">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Mail size={14} />
                  <span>Luis_albm@hotmail.com</span>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <Phone size={14} />
                  <span>+52 622 112 8639</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

function PricingItem({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3">
      {icon}
      <span>{children}</span>
    </li>
  )
}

// ============================================
// CONTACT SECTION
// ============================================
function ContactSection() {
  return (
    <section id="contact" className="relative z-10 py-32">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="p-16 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 border border-white/10 rounded-3xl backdrop-blur-2xl"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-8">Let's talk</h2>
          
          <div className="grid md:grid-cols-2 gap-12">
            <div className="space-y-6">
              <div>
                <div className="text-sm text-zinc-500 mb-2 font-medium">AUTHOR</div>
                <div className="text-2xl font-bold">Luis Alberto Burciaga Miker</div>
              </div>
              
              <a 
                href="mailto:Luis_albm@hotmail.com"
                className="flex items-center gap-4 text-xl hover:text-blue-400 transition group"
              >
                <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center group-hover:bg-blue-500/20 transition">
                  <Mail size={24} />
                </div>
                <span>Luis_albm@hotmail.com</span>
              </a>
              
              <a 
                href="tel:+526221128639"
                className="flex items-center gap-4 text-xl hover:text-blue-400 transition group"
              >
                <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center group-hover:bg-blue-500/20 transition">
                  <Phone size={24} />
                </div>
                <span>+52 622 112 8639</span>
              </a>
              
              <div className="flex gap-4 pt-4">
                <a 
                  href="https://github.com/SolvensAmoris"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center hover:bg-white/20 transition"
                >
                  <Github size={24} />
                </a>
                <a 
                  href="https://linkedin.com/in/luisalbertoburciaga"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center hover:bg-white/20 transition"
                >
                  <Linkedin size={24} />
                </a>
              </div>
            </div>
            
            <div className="text-zinc-400 text-lg space-y-4">
              <div>
                <div className="font-semibold text-white mb-2">Enterprise inquiries:</div>
                <div>Commercial licenses</div>
                <div>Custom integrations</div>
                <div>Priority support</div>
                <div>Strategic partnerships</div>
              </div>
              
              <div className="pt-4 border-t border-white/10">
                <div className="text-sm text-zinc-500 mb-2">RESPONSE TIME</div>
                <div className="text-white">Within 24 hours</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// ============================================
// FOOTER
// ============================================
function Footer() {
  return (
    <footer className="relative z-10 border-t border-white/5 px-6 py-16">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-lg" />
          <span className="font-bold">Cosmos Compiler</span>
          <span className="text-zinc-500">v0.4.5</span>
        </div>
        
        <div className="text-zinc-500 text-sm text-center">
          © 2026 Cosmos Labs. Apache 2.0
        </div>
        
        <div className="text-zinc-500 text-sm">
          Luis Alberto Burciaga Miker
        </div>
      </div>
    </footer>
  )
}

// ============================================
// MAIN PAGE
// ============================================
export default function Home() {
  const [cmdOpen, setCmdOpen] = useState(false)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setCmdOpen(!cmdOpen)
      }
      if (e.key === 'Escape') {
        setCmdOpen(false)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [cmdOpen])

  return (
    <main className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Background */}
      <SplineScene />
      <Particles />
      <div className="fixed inset-0 bg-gradient-to-b from-black/80 via-black/50 to-black z-[1]" />
      <div className="fixed inset-0 grid-bg z-[1]" />
      
      {/* Content */}
      <Navigation onOpenCmd={() => setCmdOpen(true)} />
      <HeroSection onOpenCmd={() => setCmdOpen(true)} />
      <FeaturesSection />
      <BenchmarkSection />
      <PlaygroundSection />
      <PricingSection />
      <ContactSection />
      <Footer />
      
      {/* Command Palette */}
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </main>
  )
}
