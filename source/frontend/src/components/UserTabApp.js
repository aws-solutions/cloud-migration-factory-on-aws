import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";
import User from "../actions/user";
import {List, String, TextArea, CheckBox} from "./UserInputControls";

export default class UserTabApp extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stage: props.stage,
      app: props.app,
      waves: props.waves,
      originalApp: props.app,
      isLoading: true,
      attributeType: props.attributeType,
      schema: props.schema,
      allowCreate: props.allowCreate
    };
  }

  componentWillReceiveProps(nextProps){
    // only change app the first time its recieved or if app_id changes
    if (nextProps.app.app_id !== this.props.app.app_id || Object.keys(this.state.app).length === 0){
      this.setState({
        app: nextProps.app,
        originalApp: nextProps.app,
      });
    }

    this.setState({
      isLoading: nextProps.isLoading,
      attributeType: nextProps.attributeType,
      allowCreate: nextProps.allowCreate
    });

    if (nextProps.stage !== this.props.stage){
      this.setState({
        stage: nextProps.stage
      });
    };

    if (nextProps.waves !== this.props.waves){
      this.setState({
        waves: nextProps.waves,
      });
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);

    this.setState({ isLoading: false });
    console.log(this.state.stage)
  }

  getChangedAttributes(){
    var update = {};
    const keys = Object.keys(this.state.app);

    for (var i in keys){
      const key = keys[i];
      if (this.state.originalApp[key] !== this.state.app[key]){
        update[key] = this.state.app[key];
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

  async updateApp() {
    const update = this.getChangedAttributes();

    if (Object.keys(update).length !== 0){
      this.props.setIsLoading(true);
      try {
        await this.apiUser.putApp(this.state.app.app_id, update);
        this.props.updateAppList('update', this.state.app);
        this.setState({originalApp: this.state.app});
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

  async createApp() {
    this.props.setIsLoading(true);

    let newApp = Object.assign({}, this.state.app);
    delete newApp['app_id'];

    try {
      const result = await this.apiUser.postApp(newApp);
      this.props.updateAppList('add', result);
      this.setState({
        app: result,
        originalApp: result
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

  async deleteApp() {
    this.props.setIsLoading(true);

    try {
      await this.apiUser.deleteApp(this.state.app.app_id);
      this.props.updateAppList('delete', this.state.app);
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

  onClickSaveApp = event => {
    event.preventDefault();
    if (this.state.app.app_id !== null){
      this.updateApp();
    } else {
      this.createApp();
    }
  }

  onClickDeleteApp = event => {
    event.preventDefault();
    this.deleteApp();
  }

  onChange = attrName => event => {
    var value = event.target.value;

    // flip existing value when input type is checkbox
    if (event.target.type === 'checkbox'){
      if (attrName in this.state.app){
        if (this.state.app[attrName] === false){
          value = true;
        } else {
          value = false;
        }
      }
    }

    let newState = Object.assign({}, this.state.app);
    newState[attrName] = value;
    this.setState({app: newState});
  }


  onChangeTag = attrName => event => {
    var value = event.target.value;
      var isValid = true;
    if(event.nativeEvent.inputType === "insertLineBreak")
    {

        var tagArray = value.split("\n");
        for(var i=0;i< tagArray.length;i++)
        {
          var match = tagArray[i].match(/\w+=\s?\w+,?\s?/g);
          if(match === null && tagArray[i]!== "")
            isValid = false;
        }

    }
    if(isValid){
    let newState = Object.assign({}, this.state.app);
    newState[attrName] = value;
    this.setState({app: newState});
  }
  else {
    alert("Enter tags as key value pair in format key1=value1")
  }
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
      <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">
        <div className="row px-3 pt-3"> <h3>{appLoaded?this.state.app.app_name:'Please select application'} > Application Information</h3></div>
        <form>
          <div className="row px-3 pt-3">
            <div className="col-12 px-0 pr-5">


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
                if(item.attr_name in this.state.app) {
                  value = this.state.app[item.attr_name];
                }

                if (attribute.name === 'wave_id') {

                  value = "none";
                  if (this.state.app[item.attr_name] !== undefined){
                    value = this.state.app[item.attr_name]
                  }

                  return (
                    <div key={item.attr_name} className="form-group">
                      <label>Wave ID:</label>
                      <select disabled={read_only} value={value} onChange={this.onChange(item.attr_name)} className="form-control form-control-sm">
                        <option value="none" disabled> -- select a wave id -- </option>
                        {this.state.waves.map((item, index) => {
                          return (
                            <option key={index} value={item.wave_id}>{item.wave_name}</option>
                          )
                        })}
                      </select>
                    </div>
                  )
                }
                else {
                switch(attribute.type) {
                  case 'checkbox':
                    return (
                      <CheckBox
                        key={item.attr_name}
                        onChange={this.onChange}
                        disabled={read_only}
                        label={displayName}
                        attr_name={item.attr_name}
                        value={this.state.app[item.attr_name]}
                      />
                    )

                  case 'textarea':
                    return (
                      <TextArea
                        key={item.attr_name}
                        onChange={this.onChange}
                        disabled={read_only}
                        label={displayName}
                        attr_name={item.attr_name}
                        value={this.state.app[item.attr_name]}
                      />
                    )

                  case 'tag':
                    return (
                      <TextArea
                        key={item.attr_name}
                        onBlur={this.onChangeTag}
                        onChange={this.onChangeTag}
                        disabled={read_only}
                        label={displayName}
                        attr_name={item.attr_name}
                        value={this.state.app[item.attr_name]}
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
                        disabled={read_only}
                        label={displayName}
                        attr_name={item.attr_name}
                        value={this.state.app[item.attr_name]}
                        options={options}
                      />
                    )

                  default:
                    return (
                      <String
                        key={item.attr_name}
                        onChange={this.onChange}
                        disabled={read_only}
                        label={displayName}
                        attr_name={item.attr_name}
                        value={this.state.app[item.attr_name]}
                      />
                    )
                }
              }

              })}

              <div className="row">
                <div className="col-3">
                  <input
                    className="btn btn-primary btn-outline mt-3"
                    type="button"
                    value="Save Application"
                    onClick={this.onClickSaveApp}
                  />
                </div>

                {(this.state.allowCreate && this.state.app.app_id !== null) &&
                  <div className="col-3">
                    <input
                      disabled={!('app_id' in this.state.app)}
                      onClick={this.onClickDeleteApp}
                      className="btn btn-danger btn-outline mt-3"
                      type="button"
                      value="Delete Application" />
                  </div>
                }
              </div>

            </div>
          </div>
        </form>
      </div>
      :
      <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">
        <div className="row px-3 pt-3"> <h3>No application attributes defined for this stage</h3></div>
      </div>
    );
  }
};
