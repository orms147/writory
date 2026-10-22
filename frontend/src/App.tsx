import { BrowserRouter, Route, Routes } from 'react-router';
import { InkHalo } from './components/InkHalo';
import { PublicConfigProvider } from './config/PublicConfig';
import { KeyCost } from './screens/KeyCost';
import { Library } from './screens/Library';
import { Login } from './screens/Login';
import { NotFound } from './screens/NotFound';
import { SetupSession } from './screens/setup/SetupSession';
import { Template } from './screens/setup/Template';
import { ReadBack } from './screens/story/ReadBack';
import { StoryScreen } from './screens/story/StoryScreen';
import { AuthProvider, RequireLogin, useAuth } from './state/Auth';
import { PlayerKeyProvider } from './state/PlayerKey';

// Route theo README bàn giao mục 3. Sổ tay và hỏi người kể là lớp trên `/truyen/:id`.
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Library />} />
      <Route path="/dang-nhap" element={<Login />} />
      <Route path="/khoa" element={<KeyCost />} />
      <Route path="/moi" element={<Template />} />
      <Route path="/moi/:session" element={<SetupSession />} />
      <Route path="/truyen/:id" element={<StoryScreen />} />
      <Route path="/truyen/:id/chuong/:n" element={<ReadBack />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

/** Trạng thái theo người chơi (key) dựng lại khi đổi người: đăng nhập, đăng xuất (D-89). */
function PlayerScope() {
  const s = useAuth().data;
  return (
    <PlayerKeyProvider key={s ? `${s.mode}:${s.logged_in}:${s.name ?? ''}` : ''}>
      <AppRoutes />
    </PlayerKeyProvider>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <InkHalo />
      <PublicConfigProvider>
        <AuthProvider>
          <RequireLogin>
            <PlayerScope />
          </RequireLogin>
        </AuthProvider>
      </PublicConfigProvider>
    </BrowserRouter>
  );
}
