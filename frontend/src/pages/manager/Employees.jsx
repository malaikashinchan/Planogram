import React, { useState, useEffect } from 'react';
import userService from '../../services/userService';
import Table from '../../components/Table/Table';
import Button from '../../components/Button/Button';
import Modal from '../../components/Modal/Modal';
import Input from '../../components/Input/Input';
import Select from '../../components/Select/Select';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import EmptyState from '../../components/EmptyState/EmptyState';

const Employees = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Add Employee State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState('EMPLOYEE');
  
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');
  const [addSuccess, setAddSuccess] = useState('');

  const fetchUsers = async () => {
    try {
      const data = await userService.getUsers();
      setUsers(data);
    } catch (err) {
      setError('Failed to load users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleStatus = async (user) => {
    try {
      const newStatus = user.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
      await userService.updateUserStatus(user.id, newStatus);
      setUsers(users.map(u => u.id === user.id ? { ...u, status: newStatus } : u));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user status.');
    }
  };

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`Are you sure you want to permanently delete ${user.first_name} ${user.last_name}?`)) {
      return;
    }
    try {
      await userService.deleteUser(user.id);
      setUsers(users.filter(u => u.id !== user.id));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete user.');
    }
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setAddError('');
    setAddSuccess('');
    setAdding(true);

    try {
      await userService.createUser({
        email,
        first_name: firstName,
        last_name: lastName,
        role
      });
      setAddSuccess("User created successfully! An invite email has been sent.");
      setEmail('');
      setFirstName('');
      setLastName('');
      setRole('EMPLOYEE');
      
      await fetchUsers();
      
      setTimeout(() => setIsModalOpen(false), 2000);
    } catch (err) {
      setAddError(err.response?.data?.detail || "Failed to add user.");
    } finally {
      setAdding(false);
    }
  };

  if (loading && users.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>User Management</h2>
        <Button onClick={() => {
          setIsModalOpen(true);
          setAddSuccess('');
          setAddError('');
        }}>
          + Add Employee
        </Button>
      </div>

      {users.length === 0 ? (
        <EmptyState message="No users found." />
      ) : (
        <div style={{ background: 'var(--surface-color)', padding: '1.5rem', borderRadius: '8px', boxShadow: 'var(--card-shadow)' }}>
          <Table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 500 }}>{u.first_name} {u.last_name}</td>
                  <td>{u.email}</td>
                  <td>
                    <Badge variant={u.roles.includes('ADMIN') ? 'danger' : (u.roles.includes('MANAGER') ? 'warning' : 'info')}>
                      {u.roles.join(', ')}
                    </Badge>
                  </td>
                  <td>
                    <Badge variant={u.status === 'ACTIVE' ? 'success' : 'danger'}>
                      {u.status}
                    </Badge>
                  </td>
                  <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}</td>
                  <td>
                    {!(u.roles.includes('ADMIN') || u.roles.includes('MANAGER')) ? (
                      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <button 
                          onClick={() => handleToggleStatus(u)}
                          style={{ 
                            background: 'none', 
                            border: 'none', 
                            color: u.status === 'ACTIVE' ? 'var(--warning-color)' : 'var(--success-color)', 
                            cursor: 'pointer', 
                            padding: 0,
                            fontWeight: 'bold',
                            textDecoration: 'underline'
                          }}
                        >
                          {u.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                        </button>
                        <button 
                          onClick={() => handleDeleteUser(u)}
                          style={{ 
                            background: 'none', 
                            border: 'none', 
                            color: 'var(--danger-color)', 
                            cursor: 'pointer', 
                            padding: 0,
                            fontWeight: 'bold',
                            textDecoration: 'underline'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <Modal isOpen={isModalOpen} onClose={() => !adding && setIsModalOpen(false)}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Add New User</h3>
        <ErrorMessage message={addError} />
        {addSuccess && <div style={{ color: 'green', padding: '1rem', background: '#e6ffe6', borderRadius: '4px', marginBottom: '1rem' }}>{addSuccess}</div>}
        
        <form onSubmit={handleAddSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Email Address</label>
            <Input 
              type="email"
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              placeholder="employee@company.com" 
              required 
            />
          </div>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>First Name</label>
              <Input 
                value={firstName} 
                onChange={e => setFirstName(e.target.value)} 
                required 
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Last Name</label>
              <Input 
                value={lastName} 
                onChange={e => setLastName(e.target.value)} 
                required 
              />
            </div>
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Role</label>
            <Select 
              value={role} 
              onChange={e => setRole(e.target.value)}
              required
            >
              <option value="EMPLOYEE">Employee (Mobile App / Uploads)</option>
              <option value="MANAGER">Manager (Dashboard Access)</option>
            </Select>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)} disabled={adding}>
              Cancel
            </Button>
            <Button type="submit" disabled={adding}>
              {adding ? 'Sending Invite...' : 'Create & Invite'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Employees;
