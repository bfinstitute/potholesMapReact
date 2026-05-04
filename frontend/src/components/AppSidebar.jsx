import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import bfiIconDark from '../assets/images/BFI_LogoIcon_Dark.svg';
import sidebarCloseIcon from '../assets/images/Sidebar_close.svg';
import iconChat     from '../assets/images/Icons=Chat.svg';
import iconSearch   from '../assets/images/Icons=Search.svg';
import iconSources  from '../assets/images/Icons=Sources.svg';
import iconQueue    from '../assets/images/Icons=queue.svg';
import iconBookmark from '../assets/images/Icons=Bookmark.svg';

export default function AppSidebar() {
  const [expanded, setExpanded] = useState(
    () => localStorage.getItem('buffi_sidebar_expanded') === 'true'
  );
  const [showLogout, setShowLogout] = useState(false);
  const avatarRef = useRef(null);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { logout } = useAuth();

  // Close popover when clicking outside
  useEffect(() => {
    if (!showLogout) return;
    const handler = (e) => {
      if (avatarRef.current && !avatarRef.current.contains(e.target)) {
        setShowLogout(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showLogout]);

  const handleLogout = () => {
    setShowLogout(false);
    logout();
    navigate('/');
  };

  const expand = () => {
    setExpanded(true);
    localStorage.setItem('buffi_sidebar_expanded', 'true');
  };
  const collapse = () => {
    setExpanded(false);
    localStorage.setItem('buffi_sidebar_expanded', 'false');
  };

  const isChat    = pathname === '/chat';
  const isSources = pathname === '/sources';
  const isQueue   = pathname === '/queue';

  return (
    <div className={`col-sidebar${expanded ? ' col-sidebar--expanded' : ''}`}>
      <div className="col-header col-header--sidebar">
        <button className="top-bar-logo-btn" onClick={expand} title="Open sidebar">
          <img src={bfiIconDark} alt="Buffi" className="top-bar-logo" />
        </button>
        {expanded && (
          <button className="sidebar-close-btn" onClick={collapse} title="Close sidebar">
            <img src={sidebarCloseIcon} alt="Close" className="sidebar-close-icon" />
          </button>
        )}
      </div>
      <div className={`left-icon-strip${expanded ? ' left-icon-strip--expanded' : ''}`}>
        <button
          className={`icon-strip-btn${isChat ? ' icon-strip-btn--active' : ''}`}
          title="New Chat"
          onClick={() => {
            localStorage.removeItem('buffi_active_conv');
            navigate('/chat', { state: { newConv: Date.now() } });
          }}
        >
          <img src={iconChat} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">New Chat</span>}
        </button>
        <button className="icon-strip-btn icon-strip-btn--disabled" title="Search" disabled>
          <img src={iconSearch} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Search</span>}
        </button>
        <button
          className={`icon-strip-btn${isSources ? ' icon-strip-btn--active' : ''}`}
          title="Sources"
          onClick={() => navigate('/sources')}
        >
          <img src={iconSources} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Sources</span>}
        </button>
        <button
          className={`icon-strip-btn${isQueue ? ' icon-strip-btn--active' : ''}`}
          title="Queue"
          onClick={() => navigate('/queue')}
        >
          <img src={iconQueue} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Queue</span>}
        </button>
        <button className="icon-strip-btn icon-strip-btn--disabled" title="Save" disabled>
          <img src={iconBookmark} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Save</span>}
        </button>
        <div className="strip-avatar-wrap" ref={avatarRef}>
          {showLogout && (
            <div className="avatar-popover">
              <button className="avatar-popover-btn" onClick={handleLogout}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Sign Out
              </button>
            </div>
          )}
          <button
            className="strip-avatar"
            title="Account"
            onClick={() => setShowLogout(v => !v)}
            aria-label="Account menu"
          />
        </div>
      </div>
    </div>
  );
}
