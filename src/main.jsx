import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './styles/app.css';
import { AuthProvider, ProtectedRoute } from './auth/AuthContext';
import Layout from './components/Layout';
import { Login, Register, Confirm, ForgotPassword, Welcome } from './pages/Auth';
import Dashboard from './pages/Dashboard';
import { Explore, ProjectDetail, CreateProject } from './pages/Projects';
import { FindTeammates, MyTeams, Requests, TeamManagement, StudentProfile } from './pages/Teams';
import { Profile, Notifications, Admin, NotFound } from './pages/Account';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/confirm" element={<Confirm />} />
          <Route path="/forgot" element={<ForgotPassword />} />
          <Route path="/welcome" element={<ProtectedRoute><Welcome /></ProtectedRoute>} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Explore />} />
            <Route path="projects/new" element={<CreateProject />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="teammates" element={<FindTeammates />} />
            <Route path="requests" element={<Requests />} />
            <Route path="teams" element={<MyTeams />} />
            <Route path="teams/:id" element={<TeamManagement />} />
            <Route path="profile" element={<Profile />} />
            <Route path="students/:id" element={<StudentProfile />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="admin" element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
