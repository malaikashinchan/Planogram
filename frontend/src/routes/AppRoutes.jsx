import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import ManagerLayout from '../layouts/ManagerLayout';
import EmployeeLayout from '../layouts/EmployeeLayout';

// Auth Pages
import Login from '../pages/auth/Login';
import Register from '../pages/auth/Register';
import VerifyEmail from '../pages/auth/VerifyEmail';
import ForgotPassword from '../pages/auth/ForgotPassword';
import ResetPassword from '../pages/auth/ResetPassword';

// Manager Pages
import Dashboard from '../pages/manager/Dashboard';
import Stores from '../pages/manager/Stores';
import Products from '../pages/manager/Products';
import Planograms from '../pages/manager/Planograms';
import Audits from '../pages/manager/Audits';
import Reviews from '../pages/manager/Reviews';
import Employees from '../pages/manager/Employees';

import EmployeeHome from '../pages/employee/EmployeeHome';
import AuditWizard from '../pages/employee/AuditWizard';
import AuditResult from '../pages/employee/AuditResult';

export const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Manager Routes */}
      <Route path="/manager" element={<ProtectedRoute allowedRoles={['MANAGER', 'ADMIN']} />}>
        <Route element={<ManagerLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="stores" element={<Stores />} />
          <Route path="products" element={<Products />} />
          <Route path="planograms" element={<Planograms />} />
          <Route path="audits" element={<Audits />} />
          <Route path="audits/:id" element={<AuditResult />} />
          <Route path="reviews" element={<Reviews />} />
          <Route path="employees" element={<Employees />} />
        </Route>
      </Route>

      {/* Employee Routes */}
      <Route path="/employee" element={<ProtectedRoute allowedRoles={['EMPLOYEE', 'ADMIN']} />}>
        <Route element={<EmployeeLayout />}>
          <Route index element={<EmployeeHome />} />
          <Route path="audit/new" element={<AuditWizard />} />
          <Route path="audit/:id" element={<AuditResult />} />
        </Route>
      </Route>
      
      {/* Catch all */}
      <Route path="*" element={<div>404 Not Found</div>} />
    </Routes>
  );
};
