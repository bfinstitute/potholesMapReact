import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const expand = () => {
    setExpanded(true);
    localStorage.setItem('buffi_sidebar_expanded', 'true');
  };
  const collapse = () => {
    setExpanded(false);
    localStorage.setItem('buffi_sidebar_expanded', 'false');
  };

  const isChat    = pathname === '/chat';
  const isSources = pathname === '/upload';
  const isQueue   = pathname === '/submissions';

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
          onClick={() => navigate('/chat')}
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
          onClick={() => navigate('/upload')}
        >
          <img src={iconSources} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Sources</span>}
        </button>
        <button
          className={`icon-strip-btn${isQueue ? ' icon-strip-btn--active' : ''}`}
          title="Queue"
          onClick={() => navigate('/submissions')}
        >
          <img src={iconQueue} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Queue</span>}
        </button>
        <button className="icon-strip-btn icon-strip-btn--disabled" title="Save" disabled>
          <img src={iconBookmark} alt="" className="strip-icon" />
          {expanded && <span className="strip-label">Save</span>}
        </button>
        <div className="strip-avatar" />
      </div>
    </div>
  );
}
