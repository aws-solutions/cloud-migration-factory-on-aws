import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TaskLevelEmailSettingsAttribute } from '../TaskLevelEmailSettingsAttribute';
import '@testing-library/jest-dom';

// Define types for the GroupsAttribute props
interface GroupsAttributeProps {
  attribute: {
    name: string;
    description: string;
    type: string;
    listMultiSelect?: boolean;
    listValueAPI?: string;
  };
  value: any[];
  handleUserInput: (attribute: any, value: any) => void;
  isReadonly?: boolean;
  returnErrorMessage?: (attribute: any, value: any) => string | null;
  displayHelpInfoLink?: (attribute: any) => React.ReactNode;
  [key: string]: any;
}

// Only mock the GroupsAttribute component since it's a custom component
// that would have its own tests
jest.mock('../GroupsAttribute', () => {
  return {
    __esModule: true,
    default: ({ attribute, value, handleUserInput, ...props }: GroupsAttributeProps) => (
      <div data-testid={props['data-testid'] || 'mocked-groups-attribute'}>
        <span>Mocked GroupsAttribute</span>
        <button 
          data-testid={`${props['data-testid'] || 'mocked-groups'}-change-button`}
          onClick={() => handleUserInput(attribute, ['test-value'])}
        >
          Change Value
        </button>
        <div data-testid={`${props['data-testid'] || 'mocked-groups'}-value`}>
          {JSON.stringify(value)}
        </div>
      </div>
    )
  };
});

// Create a spy for the handleUserInput function
const createMockHandleUserInput = () => {
  return jest.fn();
};

describe('TaskLevelEmailSettingsAttribute', () => {
  // Sample data for testing
  const mockItem = {
    pipeline_name: 'test-pipeline',
    pipeline_template_id: 'template-123',
    task_level_email_settings: [
      {
        task_id: 'test-pipeline:task1',
        task_name: 'task1',
        email_users: [{ email: 'user1@example.com' }],
        email_groups: [{ group_name: 'group1' }],
        email_body: 'Test email body',
        enabled: true,
        override_defaults: true
      }
    ]
  };

  const mockDataAll = {
    pipeline_template_task: {
      data: [
        {
          pipeline_template_id: 'template-123',
          pipeline_template_task_name: 'task1',
          task_id: 'task-id-1'
        },
        {
          pipeline_template_id: 'template-123',
          pipeline_template_task_name: 'task2',
          task_id: 'task-id-2'
        }
      ]
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders correctly with tasks', () => {
    const mockHandleUserInput = createMockHandleUserInput();
    
    render(
      <TaskLevelEmailSettingsAttribute
        item={mockItem}
        handleUserInput={mockHandleUserInput}
        dataAll={mockDataAll}
      />
    );

    // Check if component renders with correct header
    expect(screen.getByText('Task Level Email Notification Settings')).toBeInTheDocument();
    
    // Check if both tasks are rendered
    expect(screen.getByText('task1')).toBeInTheDocument();
    expect(screen.getByText('task2')).toBeInTheDocument();
    
    // Check if toggle buttons are rendered
    expect(screen.getByText('Enable All Task Notifications')).toBeInTheDocument();
    // Use getAllByText for elements that appear multiple times
    expect(screen.getAllByText('Enable email notifications').length).toBeGreaterThan(0);
    expect(screen.getByText('Override defaults')).toBeInTheDocument();
  });

  test('shows validation error when override defaults is enabled but no recipients', () => {
    // Create a modified item with no recipients
    const modifiedItem = {
      ...mockItem,
      task_level_email_settings: [
        {
          task_id: 'test-pipeline:task1',
          task_name: 'task1',
          email_users: [],
          email_groups: [],
          email_body: 'Test email body',
          enabled: true,
          override_defaults: true
        }
      ]
    };

    const mockHandleUserInput = createMockHandleUserInput();

    render(
      <TaskLevelEmailSettingsAttribute
        item={modifiedItem}
        handleUserInput={mockHandleUserInput}
        dataAll={mockDataAll}
      />
    );

    // Check if validation error is displayed
    const errorText = 'You must specify either email recipients or email groups when override defaults is enabled';
    expect(screen.getAllByText(errorText).length).toBeGreaterThan(0);
  });

  test('handles email users changes', async () => {
    const mockHandleUserInput = createMockHandleUserInput();
    
    render(
      <TaskLevelEmailSettingsAttribute
        item={mockItem}
        handleUserInput={mockHandleUserInput}
        dataAll={mockDataAll}
      />
    );

    // Find the users change button for task1
    const usersChangeButton = screen.getByTestId('users-value-test-pipeline:task1-change-button');
    
    // Click the button to simulate changing users
    fireEvent.click(usersChangeButton);

    // Check if handleUserInput was called with correct parameters
    await waitFor(() => {
      expect(mockHandleUserInput).toHaveBeenCalledWith([{
        field: "task_level_email_settings",
        value: expect.arrayContaining([
          expect.objectContaining({
            task_id: 'test-pipeline:task1',
            email_users: ['test-value']
          })
        ]),
        validationError: null
      }]);
    });
  });

  test('handles email groups changes', async () => {
    const mockHandleUserInput = createMockHandleUserInput();
    
    render(
      <TaskLevelEmailSettingsAttribute
        item={mockItem}
        handleUserInput={mockHandleUserInput}
        dataAll={mockDataAll}
      />
    );

    // Find the groups change button for task1
    const groupsChangeButton = screen.getByTestId('groups-value-test-pipeline:task1-change-button');
    
    // Click the button to simulate changing groups
    fireEvent.click(groupsChangeButton);

    // Check if handleUserInput was called with correct parameters
    await waitFor(() => {
      expect(mockHandleUserInput).toHaveBeenCalledWith([{
        field: "task_level_email_settings",
        value: expect.arrayContaining([
          expect.objectContaining({
            task_id: 'test-pipeline:task1',
            email_groups: ['test-value']
          })
        ]),
        validationError: null
      }]);
    });
  });

  test('renders correctly with no tasks', () => {
    const mockHandleUserInput = createMockHandleUserInput();
    
    const emptyDataAll = {
      pipeline_template_task: {
        data: []
      }
    };

    render(
      <TaskLevelEmailSettingsAttribute
        item={mockItem}
        handleUserInput={mockHandleUserInput}
        dataAll={emptyDataAll}
      />
    );

    // Check if component renders with correct header
    expect(screen.getByText('Task Level Email Notification Settings')).toBeInTheDocument();
    
    // Check that no tasks are rendered
    expect(screen.queryByText('task1')).not.toBeInTheDocument();
    expect(screen.queryByText('task2')).not.toBeInTheDocument();
  });

  test('renders correctly with no task_level_email_settings', () => {
    const mockHandleUserInput = createMockHandleUserInput();
    
    const itemWithoutRecipients = {
      pipeline_name: 'test-pipeline',
      pipeline_template_id: 'template-123'
    };

    render(
      <TaskLevelEmailSettingsAttribute
        item={itemWithoutRecipients}
        handleUserInput={mockHandleUserInput}
        dataAll={mockDataAll}
      />
    );

    // Check if component renders with correct header
    expect(screen.getByText('Task Level Email Notification Settings')).toBeInTheDocument();
    
    // Check if both tasks are rendered
    expect(screen.getByText('task1')).toBeInTheDocument();
    expect(screen.getByText('task2')).toBeInTheDocument();
    
    // Check that no override defaults toggle is visible (since tasks aren't enabled)
    expect(screen.queryByText('Override defaults')).not.toBeInTheDocument();
  });
});
