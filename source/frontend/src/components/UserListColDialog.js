import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";

export default class UserListColDialog extends Component {
  constructor(props) {
    super(props);

    this.state = {
      showColumns: this.props.showColumns,
      schemaApp : [],
      schemaServer : [],
      showDialog: this.props.showDialog,
      type: this.props.type
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);
    this.getSchema();
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog,
      showColumns: nextProps.showColumns
    });
  }

  async getSchema() {
    try {
      var response = await this.apiAdmin.getSchemaApp();
      this.setState({ schemaApp : response['attributes']});

      response = await this.apiAdmin.getSchemaServer();
      this.setState({ schemaServer : response['attributes']});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  onClickCancelDialog = event => {
    this.setState({
      showColumns: this.props.showColumns
    });
    this.props.closeDialog();
  }

  onClickUpdateView = event => {
    this.props.closeDialog();
    this.props.onClickUpdateView(this.state.showColumns);
  }

  onChangeDialog = event => {

    if(this.state.showColumns.includes(event.target.name)){
      var newColumnList = [];
      for (var item in this.state.showColumns) {
        if (this.state.showColumns[item] !== event.target.name){
          newColumnList.push(this.state.showColumns[item]);
        }
        this.setState({showColumns: newColumnList});
      }
    } else {
      let newColumnList = this.state.showColumns.slice();
      newColumnList.push(event.target.name);
      this.setState({showColumns: newColumnList});
    }
  }

  render() {
    let styles = this.state.showDialog
      ? { display: "block" }
      : { display: "none" };
    return (
      <div>
        {this.state.showDialog &&
          <div>
            <div className="block-events-full"> </div>
            <div class="modal fade show" data-backdrop="static" style={styles} id="ModalCenter" tabindex="-1" role="dialog" aria-labelledby="ModalCenterTitle" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="ModalLongTitle">
                <div className="pb-4">
                <b>Show/Hide Columns</b>
                </div>
                </h5>
                    <span onClick={this.onClickCancelDialog} className="onhover float-right">
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">&times;
                        </button>
                    </span>
              </div>
              <div class="modal-body">
              <div style={{height:"220px",overflow:"auto"}}>
                <div className="row">

                  {(this.state.type === 'both' || this.state.type === 'app') &&
                    <div className={this.state.type === 'both'?"col-6":"col-12"}>
                      <div>Application Attributes</div>
                      <hr />
                      <ul style={{listStyleType: "none"}} className="p-0 m-0">
                        {this.state.schemaApp.map((item, index) => {
                          if (item.name === "app_name" || item.name === "app_id") {
                            return null
                          }

                          return (
                            <li key={item.name}>
                              <input
                                onChange={this.onChangeDialog}
                                type="checkbox"
                                name={item.name}
                                checked={this.state.showColumns.includes(item.name)}
                                className="mr-3"
                              />
                              {item.name}
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  }

                  {(this.state.type === 'both' || this.state.type === 'server') &&
                    <div className={this.state.type === 'both'?"col-6":"col-12"}>
                      <div>Server Attributes</div>
                      <hr />
                      <ul style={{listStyleType: "none"}} className="p-0 m-0">
                        {this.state.schemaServer.map((item, index) => {
                          if (item.name === "server_name" || item.name === "server_id") {
                            return null
                          }

                          return (
                            <li key={item.name}>
                              <input
                                onChange={this.onChangeDialog}
                                type="checkbox"
                                name={item.name}
                                checked={this.state.showColumns.includes(item.name)}
                                className="mr-3"
                              />
                              {item.name}
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  }

                </div>

              </div>
              <hr />
              <input
                className="btn btn-primary btn-outline mt-3 mr-3 float-right"
                type="button"
                value="Update View"
                onClick={this.onClickUpdateView}
              />
              </div>
            </div>
          </div>
        </div>
          </div>
        }
    </div>
    )
  }
}
