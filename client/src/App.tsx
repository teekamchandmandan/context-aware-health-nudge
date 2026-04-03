import { Routes, Route, Navigate } from 'react-router-dom';
import MemberPage from './pages/MemberPage';
import CoachPage from './pages/CoachPage';

function App() {
  return (
    <Routes>
      <Route path='/member' element={<MemberPage />} />
      <Route path='/coach' element={<CoachPage />} />
      <Route
        path='*'
        element={<Navigate to='/member?memberId=member_meal_01' replace />}
      />
    </Routes>
  );
}

export default App;
