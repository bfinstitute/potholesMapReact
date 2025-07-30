import { useState } from 'react';
import '../styles/Header.css';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <header className="site-header">
      <div className="container">
        <div className="branding">
          <div className="logo">
            <img src="/Logo Container.png" alt="Better Futures Institute Logo" className="logo-image" />
          </div>
        </div>
        <div className="header-actions">
          <div className="chat-icon">
            <img src="/Chat Message Icon.png" alt="Chat Message" className="chat-icon-image" />
          </div>
          <button className="hamburger-menu" onClick={toggleMenu}>
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
        
        {/* Navigation Menu */}
        {isMenuOpen && (
          <div className="nav-menu">
            <a href="/" className="nav-link">Home</a>
            <a href="/about" className="nav-link">About</a>
          </div>
        )}
      </div>
    </header>
  );
}