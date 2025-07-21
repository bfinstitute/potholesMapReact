import '../styles/Header.css';

export default function Header() {
  return (
    <header className="site-header">
      <div className="container">
        <div className="branding">
          {/* <img src="/logo.png" alt="Houston Data" className="logo" /> */}
          <h1>San Antonio Potholes</h1>
        </div>
        <nav className="nav-links">
          <a href="/">Home</a>
          {/* <a href="#indicators">Indicators</a>
          <a href="#map">Map</a>
          <a href="#upload">Upload CSV</a> */}
          <a href="#about">About</a>
        </nav>
      </div>
    </header>
  );
}