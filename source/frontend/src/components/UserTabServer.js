import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";
import User from "../actions/user";
import {List, String, MultiValueString, TextArea, CheckBox, Tag} from "./UserInputControls";

export default class UserTabServer extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stage: props.stage,
      app: props.app,
      isLoading: true,
      attributeType: props.attributeType,
      appServers: props.appServers,
      selectedServer: {},
      schema: props.schema,
      allowCreate: props.allowCreate
    };
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.app.app_id !== this.props.app.app_id || Object.keys(this.state.app).length === 0){
      this.setState({
        app: nextProps.app,
        selectedServer: {}
      });
    }

    this.setState({
      isLoading: nextProps.isLoading,
      attributeType: nextProps.attributeType,
      allowCreate: nextProps.allowCreate,
      appServers: nextProps.appServers
    });

    if (nextProps.stage !== this.props.stage){
      this.setState({
        stage: nextProps.stage
      });
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);

    this.setState({ isLoading: false });
  }

  getChangedAttributes(){
    var update = {};
    var selectedServerIndex;

    // Get the index of selected server in the app sever list
    for (var i in this.state.appServers){
      if (this.state.appServers[i].server_id === this.state.selectedServer.server_id) {
        selectedServerIndex = i;
      }
    }

    // Compare the selected server to the orignal server list and extract key values that are different
    const keys = Object.keys(this.state.selectedServer);
    for (i in keys){
      const key = keys[i];
      if (this.state.selectedServer[key] !== this.state.appServers[selectedServerIndex][key]){
        update[key] = this.state.selectedServer[key];
      }
    }

    return update;
  }

  getAttribute(attribute){
    for (var i in this.state.schema){
      if (this.state.schema[i].name === attribute){
        return this.state.schema[i];
      }
    }
    return {}
  }

  async updateServer() {
    const update = this.getChangedAttributes();

    if (Object.keys(update).length !== 0){
      this.props.setIsLoading(true);

      try {
        await this.apiUser.putServer(this.state.selectedServer.server_id, update);
        this.props.updateServerList('update', this.state.selectedServer);

      } catch (e) {
        console.log(e);
        if ('response' in e && 'data' in e.response) {
          this.props.showError(e.response.data);
        } else{
          this.props.showError('Unknown error occured')
        }
      }
      this.props.setIsLoading(false);
    }
  }

  async createServer() {
    this.props.setIsLoading(true);

    let newServer = Object.assign({}, this.state.selectedServer);
    delete newServer['server_id'];

    try {
      const result = await this.apiUser.postServer(newServer);
      this.setState({
        selectedServer: result
      });
      this.props.updateServerList('add', this.state.selectedServer);
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
    this.props.setIsLoading(false);
  }


  async deleteServer() {
    this.props.setIsLoading(true);

    try {
      await this.apiUser.deleteServer(this.state.selectedServer.server_id);
      this.props.updateServerList('delete', this.state.selectedServer);

      this.setState({
        selectedServer: {}
      });
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
    this.props.setIsLoading(false);
  }

  onClickSaveServer = event => {
    event.preventDefault();
    if (this.state.selectedServer.server_id !== null){
      this.updateServer();
    } else {
      this.createServer();
    }
  }

  onClickDeleteServer = event => {
    event.preventDefault();
    this.deleteServer();
  }

  onChange = (attrName,type) => event => {
    let newState = Object.assign({}, this.state.selectedServer);
    if (type === 'tag') {
      var tags=[]
      var newtags=[]
      tags = event.target.value.split("\n")
      for (var i = 0; i < tags.length; i++) {
        var tagpair
        tagpair = tags[i].split("=")
        newtags.push({
          key:   tagpair[0],
          value: tagpair[1]
         });
      }
      newState[attrName] = newtags;
    }
    if (type === 'multivalue-string') {
      var values=[]
      values = event.target.value.split(",")
      newState[attrName] = values;
    }
    else {
      newState[attrName] = event.target.value;
    }
    this.setState({selectedServer: newState});
  }

  onChangeTag = attrName => event => {
    var value = event.target.value;
    var isValid = true;
    if(value === "=")
      return;
    var newtags=[]
    var tagArray = value.split("\n");
    for(var i=0;i< tagArray.length;i++)
    {
      if(event.nativeEvent.inputType === "insertLineBreak")
      {
      var match = tagArray[i].match(/\w+=\s?\w+,?\s?/g);
      if(match === null && tagArray[i]!== "")
        isValid = false;
      }
      if (tagArray[i].includes("=")) {
      var tagpair = tagArray[i].split("=")
        newtags.push({
          key:   tagpair[0],
          value: tagpair[1]
         });
        }
      else {
        newtags.push(
          tagArray[i]
         );
      }
    }

    if(isValid){
    let newState = Object.assign({}, this.state.selectedServer);
    newState[attrName] = newtags;
    this.setState({selectedServer: newState});
  }
  else {
    alert("Enter tags as key value pair in format key1=value1")
    }
  }

  onClickSelectServer = server_id => event => {
    event.preventDefault();
    for (var i in this.state.appServers){
      if (this.state.appServers[i].server_id === server_id) {
        this.setState({selectedServer: this.state.appServers[i]});
      }
    }
  }

  onClickCreateNew = event => {
    event.preventDefault();

    const newServer = {
      server_name: 'New server',
      server_id: null,
      app_id: this.state.app.app_id
    }

    this.setState({
      selectedServer: newServer
    })
  }

  render() {
    var appLoaded = false;
    if (Object.keys(this.state.app).length > 0){
      appLoaded = true;
    }

    var hasAttributes = false;
    if ('attributes' in this.state.stage){
      for (var i in this.state.stage.attributes){
        if (this.state.stage.attributes[i].attr_type === this.state.attributeType){
          hasAttributes = true;
        }
      }
    }

    return (
      hasAttributes?
        <div id="factory-tab-container" className="container-fluid rounded bg-white py-3">
          <div className="row px-3 pt-3"> <h3>{appLoaded?this.state.app.app_name:'Please select application'} > Server List</h3></div>
          <div className="row px-3 pt-3">
            <div className="col-4 px-0 pr-5">

              {this.state.allowCreate &&
                <div className="pb-3"><a href="." onClick={this.onClickCreateNew}>+ Create new server</a></div>
              }

                <table className="table table-hover">
                  <tbody>
                    {(this.state.appServers.length === 0) &&
                      <tr>
                        <td>No servers found</td>
                      </tr>
                    }
                    {this.state.appServers.map((item, index) => {
                      var style = ''
                      if (item.server_id === this.state.selectedServer.server_id){
                        style = 'bg-grey'
                      }
                      return (
                        <tr key={item.server_id} className={style} onClick={this.onClickSelectServer(item.server_id)}>
                          <td>{item.server_name}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="col-8">
                <form>
                  <div className="row">
                    <div className="col-12">

                        {this.state.stage.attributes.map((item, index) => {

                          if(item.attr_type !== this.state.attributeType){
                            return null;
                          }

                          var read_only = false
                          if ('read_only' in item) {
                            if (item['read_only'] === true) {
                              read_only = true
                            }
                          }

                          const attribute = this.getAttribute(item.attr_name);

                          var displayName;
                          if ('description' in attribute) {
                            displayName=attribute.description;
                          } else {
                            displayName=item.attr_name;
                          }

                          var value='';
                          if(item.attr_name in this.state.selectedServer) {
                            value = this.state.selectedServer[item.attr_name];
                          }

                          switch(attribute.type) {
                            case 'checkbox':
                              return (
                                <CheckBox
                                  key={item.attr_name}
                                  onChange={this.onChange}
                                  disabled={!('server_id' in this.state.selectedServer) || read_only}
                                  label={displayName}
                                  attr_name={item.attr_name}
                                  value={value}
                                />
                              )

                            case 'multivalue-string':
                              return (
                                <MultiValueString
                                key={item.attr_name}
                                onChange={this.onChange}
                                disabled={!('server_id' in this.state.selectedServer) || read_only}
                                label={displayName}
                                attr_name={item.attr_name}
                                value={value}
                            />

                              )
                            case 'textarea':
                              return (
                                <TextArea
                                  key={item.attr_name}
                                  onChange={this.onChange}
                                  disabled={!('server_id' in this.state.selectedServer) || read_only}
                                  label={displayName}
                                  attr_name={item.attr_name}
                                  value={value}
                                />
                              )

                            case 'tag':
                              var tags='';
                              for (i = 0; i < value.length; i++) {
                                if (value[i].hasOwnProperty("key")) {
                                tags = tags + value[i]['key'] + '=' + value[i]['value'] + '\n'
                                }
                                else {
                                  tags = tags + value[i] + '\n'
                                }
                              }
                              tags = tags.slice(0, -1)
                              return (
                                <Tag
                                  key={item.attr_name}
                                  onChange={this.onChangeTag}
                                  disabled={!('server_id' in this.state.selectedServer) || read_only}
                                  label={displayName}
                                  attr_name={item.attr_name}
                                  value={tags}
                                />
                              )

                            case 'list':
                              var options = '';
                              if ('listvalue' in attribute){
                                options = attribute.listvalue;
                              }
                              return (
                                <List
                                  key={item.attr_name}
                                  onChange={this.onChange}
                                  disabled={!('server_id' in this.state.selectedServer) || read_only}
                                  label={displayName}
                                  attr_name={item.attr_name}
                                  value={this.state.selectedServer[item.attr_name]}
                                  options={options}
                                />
                              )

                            default:
                              return (
                                <String
                                  key={item.attr_name}
                                  onChange={this.onChange}
                                  disabled={!('server_id' in this.state.selectedServer) || read_only}
                                  label={displayName}
                                  attr_name={item.attr_name}
                                  value={value}
                                />
                              )
                          }
                        }

                        )}

                    </div>
                  </div>
                </form>
                <div className="row">
                  <div className="col-3">
                    <input disabled={!('server_id' in this.state.selectedServer)} onClick={this.onClickSaveServer} className="btn btn-primary btn-outline mt-3" type="button" value="Save Server" />
                  </div>
                  {(this.state.allowCreate && this.state.selectedServer.server_id !== null) &&
                    <div className="col-3">
                      <input disabled={!('server_id' in this.state.selectedServer)} onClick={this.onClickDeleteServer} className="btn btn-danger btn-outline mt-3" type="button" value="Delete Server" />
                    </div>
                  }
               </div>
              </div>
            </div>
        </div>
        :
        <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">
          <div className="row px-3 pt-3"> <h3>No server attributes defined for this stage</h3></div>
        </div>
    );
  }
};
