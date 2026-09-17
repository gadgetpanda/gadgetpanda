import Link from "next/link";

const links = [
  { href: "/store", label: "Store" },
  { href: "/world", label: "PandaWorld" },
  { href: "/lab", label: "Lab" },
  { href: "/news", label: "News" },
  { href: "/support", label: "Support" },
];

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Link href="/" className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.jpg" alt="" width={36} height={36} />
          <span>Gadget Panda</span>
        </Link>
        <nav className="nav" aria-label="Primary">
          {links.map((link) => (
            <Link key={link.href} href={link.href}>
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="header-cta">
          <Link href="/lab" className="btn btn-ghost">
            Open Lab
          </Link>
          <Link href="/store" className="btn btn-primary">
            Buy
          </Link>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell footer-inner">
        <div>
          <strong>Gadget Panda</strong>
          <p>IDEA → CODE → PROTOTYPE → COMMUNITY</p>
        </div>
        <div className="footer-links">
          <a href="https://pypi.org/project/gadgetpanda/" rel="noreferrer">
            PyPI
          </a>
          <a href="https://github.com/gadgetpanda/gadgetpanda" rel="noreferrer">
            GitHub
          </a>
          <a href="https://lib.gadgetpanda.app" rel="noreferrer">
            License
          </a>
          <Link href="/support">Support</Link>
        </div>
      </div>
    </footer>
  );
}
