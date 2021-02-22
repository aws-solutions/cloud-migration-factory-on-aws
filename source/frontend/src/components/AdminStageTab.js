import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";

export default class AdminStageTab extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stage: props.stage,
      isLoading: true,
      waveAttributes: {attributes:[]},
      appAttributes: {attributes:[]},
      serverAttributes: {attributes:[]},
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading
    });

    if (nextProps.stage !== this.props.stage){
      this.setState({
        stage: nextProps.stage
      });
    };

    // API requires attributes key, add empty attributes if stage is loaded and does not have attributes
    if (Object.keys(this.state.stage).length > 0 && !('attributes' in this.state.stage)){
      let newStage = Object.assign({}, this.state.stage);
      newStage.attributes = [];
      this.setState({stage: newStage});
    }
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.api = await new Admin(session);

    try {
      const schemaWave = await this.api.getSchemaWave();
      if ('attributes' in schemaWave) {
        this.setState({ waveAttributes: schemaWave});
      }

      const schemaApp = await this.api.getSchemaApp();
      if ('attributes' in schemaApp) {
        this.setState({ appAttributes: schemaApp});
      }

      const schemaServer = await this.api.getSchemaServer();
      if ('attributes' in schemaServer) {
        this.setState({ serverAttributes : schemaServer});
      }

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }

    this.setState({ isLoading: false });
  }

  async updateStage() {
    this.setState({isLoading: true});

    try {
      await this.api.putStage(this.state.stage);
      this.props.updateStageList('update', this.state.stage);
    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  async createStage() {
    this.setState({isLoading: true});

    try {
      const response = await this.api.postStage(this.state.stage);

      this.setState({ stage: response});
      this.props.updateStageList('add', this.state.stage);

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  async deleteStage() {
    this.setState({isLoading: true});

    try {
      await this.api.delStage(this.state.stage.stage_id);

      this.props.updateStageList('delete', this.state.stage);
      this.setState({stage: {} });

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  onClickSaveStage = event => {
    event.preventDefault();
    if (this.state.stage.stage_id === null){
      this.createStage();
    } else {
      this.updateStage();
    }
  }

  onClickDeleteStage = event => {
    event.preventDefault();
    this.deleteStage();
  }

  onChangeAppName = event => {
    let newStage = Object.assign({}, this.state.stage);
    newStage.stage_name = event.target.value.trim();
    this.setState({stage: newStage});
  }

  onClickRemoveAttribute = id => event => {
    event.preventDefault();

    for (var i = 0; i < this.state.stage.attributes.length; i++) {
      if (id === this.state.stage.attributes[i].attr_name) {
        let newAttributes = Array.from(this.state.stage.attributes);
        newAttributes.splice(i, 1);;

        let newStage = Object.assign({}, this.state.stage);
        newStage.attributes = newAttributes;

        this.setState({stage: newStage});
      }
    }
  }

  onClickAddAttribute = type => event => {
    this.refs.waveAttributes.blur();
    this.refs.appAttributes.blur();
    this.refs.serverAttributes.blur();
    var alreadyExists = false;

    if ('attributes' in this.state.stage) {
      for (var i = 0; i < this.state.stage.attributes.length; i++) {
        if (event.target.value === this.state.stage.attributes[i].attr_name) {
          alreadyExists = true;
        }
      }
    }

    if (!alreadyExists) {
      const newAttribute = {
        attr_name: event.target.value,
        attr_type: type
      }

      let newStage = Object.assign({}, this.state.stage);

      if (!('attributes' in newStage)){
        newStage.attributes = [];
      }
      newStage.attributes.push(newAttribute);

      this.setState({stage: newStage});
    }
  }

  onChangeReadOnly = event => {
    let newStage = Object.assign({}, this.state.stage);
    for (var i = 0; i < this.state.stage.attributes.length; i++) {
      if (event.target.name === this.state.stage.attributes[i].attr_name) {

        newStage.attributes[i].read_only = event.target.checked;

        this.setState({stage: newStage});
        return;
      }
    }
  }

  render() {
    var stageLoaded = false;
    if (Object.keys(this.state.stage).length > 0){
      stageLoaded = true;
    }

    return (
      <div>
        {this.state.isLoading?<div className="block-events" ></div>:null}
        <div className="pt-3">
          <h4>> {stageLoaded?this.state.stage.stage_name:'No stage selected'}</h4>
        </div>

        <div id="factory-tab" className="container-fluid rounded  py-3 px-0">
          <ul className="nav nav-tabs">
            <li className="nav-item">
              <span className="nav-link active">Stage Configuration {this.state.isLoading?<i className="fa fa-spinner fa-spin"></i>:null}</span>
            </li>
          </ul>

          <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">

            <div className="row px-3 pt-3"> <h3>{stageLoaded?this.state.stage.stage_name:'Please select stage'} > Stage Configuration</h3></div>
            <form>
              <div className="row px-3 pt-3">
                <div className="col-6 px-0 pr-5">
                  <div className="form-group">
                    <label htmlFor="appName">Name:</label>
                    <input
                      disabled={!stageLoaded}
                      type="text"
                      key={this.state.stage.stage_id}
                      className="form-control form-control-sm"
                      onChange={this.onChangeAppName}
                      defaultValue={this.state.stage.stage_name}
                      ref="appName"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="attribute">Add Wave Attribute:</label>
                    <select disabled={!stageLoaded} ref="waveAttributes" onChange={this.onClickAddAttribute('wave')} value={'none'} className="form-control form-control-sm" id="attribute">
                      <option value="none" disabled>Select attribute to add</option>
                      {this.state.waveAttributes.attributes.map((item, index) => {
                        return (
                          <option key={item.name} value={item.name}>{item.name}</option>
                        )
                      })}
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="attribute">Add Application Attribute:</label>
                    <select disabled={!stageLoaded} ref="appAttributes" onChange={this.onClickAddAttribute('app')} value={'none'} className="form-control form-control-sm" id="attribute">
                      <option value="none" disabled>Select attribute to add</option>
                      {this.state.appAttributes.attributes.map((item, index) => {
                        return (
                          <option key={item.name} value={item.name}>{item.name}</option>
                        )
                      })}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="attribute">Add Server Attribute:</label>
                    <select disabled={!stageLoaded} ref="serverAttributes" onChange={this.onClickAddAttribute('server')} value={'none'} className="form-control form-control-sm" id="attribute">
                      <option value="none" disabled>Select attribute to add</option>
                      {this.state.serverAttributes.attributes.map((item, index) => {
                        return (
                          <option key={item.name} value={item.name}>{item.name}</option>
                        )
                      })}
                    </select>
                  </div>

                  <input
                    disabled={!stageLoaded}
                    className="btn btn-primary btn-outline mt-3 mr-3"
                    type="button"
                    value="Save Stage"
                    onClick={this.onClickSaveStage}
                  />
                  <input
                    disabled={!stageLoaded || this.state.stage.stage_id === null}
                    className="btn btn-danger btn-outline mt-3"
                    type="button"
                    value="Delete Stage"
                    onClick={this.onClickDeleteStage}
                  />
                </div>
                <div className="col-6 px-0 pr-5">

                  <div className="pb-2">
                    Attributes linked to current stage:
                  </div>
                  <table className="table table-hover">
                    <tbody>
                      {'attributes' in this.state.stage &&
                          this.state.stage.attributes.map((item, index) => {
                          return (
                            <tr key={item.attr_name}>
                              <td><span onClick={this.onClickRemoveAttribute(item.attr_name)} className="pr-3 text-danger">x</span> {item.attr_name}</td>
                              <td>  <input
                                        onChange={this.onChangeReadOnly}
                                         name={item.attr_name}
                                         className="mr-3"
                                       checked={item.read_only}
                                       type="checkbox"/>
                                     <label htmlFor="readOnly">Is Read Only</label></td>
                            </tr>
                          )
                        })
                      }

                      {(!('attributes' in this.state.stage)|| (this.state.stage.attributes.length === 0)) &&
                        <tr>
                          <td>No attributes linked to stage</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>

    );
  }
};
