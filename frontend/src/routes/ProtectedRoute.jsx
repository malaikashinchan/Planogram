import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

export const ProtectedRoute = ({ allowedRoles }) => {
  const { isAuthenticated, user, loading } = useContext(AuthContext);

  if (loading) {
    return <div>Loading...</div>; // Could use Spinner later
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // If roles are specified, check them
  if (allowedRoles && user && user.roles) {
    const hasRole = user.roles.some(role => allowedRoles.includes(role));
    if (!hasRole) {
      if (user.roles.includes('MANAGER') || user.roles.includes('ADMIN')) return <Navigate to="/manager" replace />;
      if (user.roles.includes('EMPLOYEE')) return <Navigate to="/employee" replace />;
      return <Navigate to="/" replace />;
    }
  }

  return <Outlet />;
};
