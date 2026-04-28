import AppLayout from './AppLayout';
import ToggleSwitch from './ToggleSwitch';
import '../styles/CSVEditor.css';

export default function CSVEditor() {
  return (
    <AppLayout>
      <div className='preview-page'>
        <ToggleSwitch />
      </div>
    </AppLayout>
  );
}
