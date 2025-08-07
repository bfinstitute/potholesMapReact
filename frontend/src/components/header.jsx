import '../styles/Header.css';
import mainLogo from '../assets/images/BFI_Logo.svg'
import menuLogo from '../assets/images/iconoir_menu.svg'
import mainLogoIcon from '../assets/images/BFI_LogoIcon.svg'

export default function Header() {
  return (
    <header className="site-header">
      <div className="container">
        <div className="branding">
          <a href="/">
            <img src={mainLogo} alt="Better Futures Institute"/>
          </a>
        </div>
        <nav className="nav-links">
          {/* <a href="/">Home</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#upload">Upload CSV</a> */}
          {/* <a href="/">
            <img src={mainLogoIcon} alt="Better Futures Institute" className='header-base-btn header-img'/>
          </a>
          <button className='header-base-btn header-menu-btn'><img src={menuLogo} alt="="/></button> */}
        </nav>
      </div>
    </header>
  );
}