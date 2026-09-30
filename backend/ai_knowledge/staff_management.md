# Staff Management

## Overview

The Staff page (also called the Employees page) is accessible from the sidebar under **"Staff"** at the route `/manager/employees`. It is available to Managers and Admins only.

## What Managers Can Do on the Staff Page

### View Staff
- See a table of all employees in the organization
- Columns: Name, Email, Role (EMPLOYEE/ADMIN), Status (ACTIVE/INACTIVE), Last Login, Actions

### Add a New Employee
- Click the **"+ Add Employee"** button in the top-right of the Staff page
- Fill in the employee's name, email, and password
- The new employee will be assigned the EMPLOYEE role by default
- After creation, the employee can log in and perform audits

### Deactivate an Employee
- Click the **"Deactivate"** button next to an employee
- This disables their account without permanently deleting it
- A deactivated employee cannot log in
- The deactivation can be reversed

### Delete an Employee
- Click the **"Delete"** button next to an employee
- This permanently removes the employee from the organization
- This action cannot be undone

## Navigation

Users can navigate to the Staff page by:
- Clicking "Staff" in the left sidebar
- Asking the assistant: "take me to staff page", "show employees", "add new employee", "manage team"

## Roles

- **ADMIN**: Full access — can add, deactivate, and delete any user
- **MANAGER**: Can manage employees
- **EMPLOYEE**: Cannot access the Staff page

## Common Questions

**Q: How do I add a new employee?**
Go to the Staff page (`/manager/employees`) and click the "+ Add Employee" button.

**Q: How do I disable an employee's access?**
Go to the Staff page and click "Deactivate" next to that employee.

**Q: Can employees manage other employees?**
No. Only Managers and Admins can access the Staff page.
