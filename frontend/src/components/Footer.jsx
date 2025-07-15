import '../styles/Footer.css';

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <h3 className="footer-title">San Antonio Potholes</h3>
        <div className="footer-links">
          <a href="/">Home</a>
          <a href="/about">About</a>
          <a href="/data">Data</a>
          <a href="/contact">Contact</a>
        </div>
        <p className="footer-copy">&copy; {new Date().getFullYear()} All rights reserved.</p>
      </div>
    </footer>
  );
}
