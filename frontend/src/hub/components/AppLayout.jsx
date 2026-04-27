import AppSidebar from '../../components/AppSidebar';
import '../styles/AppLayout.css';

export default function AppLayout({ children }) {
  return (
    <div className="app-wrapper">
      <AppSidebar />
      <main className="app-main">
        {children}
      </main>
    </div>
  );
}
