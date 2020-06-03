import React from "react";

export default class AdminRoleList extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      roles: props.roles,
      isLoading: props.isLoading,
      selectedRole: ''
    };
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.roles !== this.props.roles){
      this.setState({
        roles: nextProps.roles,
        isLoading: nextProps.isLoading,
        selectedRole: nextProps.selectedRole
      });
    };
  }

  render() {
    return (
      <div className="container-fluid rounded service-list">
        <div className="pb-2 pt-3">
          <a href="." onClick={this.props.onClickCreateNew}>+ Create new role</a>
        </div>
        <div className="tableFixHead">
          <table className={"table " + (this.state.isLoading?null:'table-hover')}>
            <tbody>
              {this.state.isLoading?<tr><td><i className="fa fa-spinner fa-spin"></i> Loading Roles...</td></tr>:null}
              {this.state.roles.map((item, index) => {
                var style = ''
                if (item.role_id === this.props.selectedRole){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.role_id} className={style} onClick={this.props.onClick(item.role_id)}>
                    <td>{item.role_name}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
};
