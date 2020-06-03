

import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";

export default class AdminAttributeTab extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      stage: props.stage,
      selectedAppAttribute: props.selectedAppAttribute,
      selectedServerAttribute: props.selectedServerAttribute,
      AppAttributeData: props.AppAttributeData,
      ServerAttributeData: props.ServerAttributeData,
      type: props.type,
      isLoading: true,
      isListType: props.isListType,
      listtypes: props.listtypes,
      PendingChangeAppAttr: '',
      PendingChangeServerAttr: '',
      PendingChangeAppName: '',
      PendingChangeServerName: '',
      appAttributes: {attributes:[]},
      serverAttributes: {attributes:[]}
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading
    });
    if (nextProps.selectedAppAttribute !== this.props.selectedAppAttribute){
      this.setState({
        selectedAppAttribute: nextProps.selectedAppAttribute
      });
    };
    if (nextProps.listtypes !== this.props.listtypes){
      this.setState({
        listtypes: nextProps.listtypes
      });
    };
    if (nextProps.isListType !== this.props.isListType){
      this.setState({
        isListType: nextProps.isListType
      });
    };

    if (nextProps.selectedServerAttribute !== this.props.selectedServerAttribute){
      this.setState({
        selectedServerAttribute: nextProps.selectedServerAttribute
      });
    };
    if (nextProps.type !== this.props.type){
      this.setState({
        type: nextProps.type
      });
    };
    if (nextProps.AppAttributeData !== this.props.AppAttributeData){
      this.setState({
        AppAttributeData: nextProps.AppAttributeData
      });
    };
    if (nextProps.ServerAttributeData !== this.props.ServerAttributeData){
      this.setState({
        ServerAttributeData: nextProps.ServerAttributeData
      });
    };
    if (nextProps.PendingChangeAppAttr !== this.props.AppAttributeData){
      this.setState({
        PendingChangeAppAttr: nextProps.AppAttributeData
      });
    };
    if (nextProps.PendingChangeAppName !== this.props.selectedAppAttribute){

      this.setState({
        PendingChangeAppName: nextProps.selectedAppAttribute
      });
    };
    if (nextProps.PendingChangeServerAttr !== this.props.ServerAttributeData){
      this.setState({
        PendingChangeServerAttr: nextProps.ServerAttributeData
      });
    };
    if (nextProps.PendingChangeServerName !== this.props.selectedServerAttribute){
      this.setState({
        PendingChangeServerName: nextProps.selectedServerAttribute
      });
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.api = await new Admin(session);

    try {
      const schemaApp = await this.api.getSchemaApp();
      this.setState({ appAttributes: schemaApp});

      const schemaServer = await this.api.getSchemaServer();
      this.setState({ serverAttributes : schemaServer});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }

    this.setState({ isLoading: false });
  }

  async deleteAttr() {
    this.setState({isLoading: true});

    try {
      if (this.state.type === 'app') {
      await this.api.delAppSchemaAttr(this.state.PendingChangeAppName);
      this.props.updateAttrList('delete', this.state.PendingChangeAppName, 'app');
      }
      if (this.state.type === 'server') {
        await this.api.delSerSchemaAttr(this.state.PendingChangeServerName);
        this.props.updateAttrList('delete', this.state.PendingChangeServerName, 'server');
        }

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response);
      }
    }
    this.setState({isLoading: false});
  }

  async createAttr() {
    this.setState({isLoading: true});

    try {
      if (this.state.type === 'app') {
        await this.api.postAppSchemaAttr(this.state.PendingChangeAppAttr);
        this.props.updateAttrList('add', this.state.PendingChangeAppAttr, 'app');
      }
      if (this.state.type === 'server') {
        await this.api.postServerSchemaAttr(this.state.PendingChangeServerAttr);
        this.props.updateAttrList('add', this.state.PendingChangeServerAttr, 'server');
      }
    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  async updateAttr() {
    this.setState({isLoading: true});

    try {
      if (this.state.type === 'app') {
      await this.api.putAppSchemaAttr(this.state.PendingChangeAppAttr, this.state.PendingChangeAppName);
      this.props.updateAttrList('update', this.state.PendingChangeAppAttr, 'app');
      }
      if (this.state.type === 'server') {
        await this.api.putServerSchemaAttr(this.state.PendingChangeServerAttr, this.state.PendingChangeServerName);
        this.props.updateAttrList('update', this.state.PendingChangeServerAttr, 'server');
        }
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  onChangeAttrName = type => event => {
    if (this.state.type === 'app'){
    if (type === 'name') {
      let newAttr = Object.assign({}, this.state.AppAttributeData);
      newAttr.name = event.target.value.trim();
    this.setState({
      PendingChangeAppAttr: newAttr,
      AppAttributeData: newAttr
    })
    }
    if (type === 'description') {
      let newAttr = Object.assign({}, this.state.AppAttributeData);
      newAttr.description = event.target.value;
    this.setState({
      PendingChangeAppAttr: newAttr,
      AppAttributeData: newAttr
    })
    }
    if (type === 'type') {
      let newAttr = Object.assign({}, this.state.AppAttributeData);
      newAttr.type = event.target.value;
      if (event.target.value === 'list') {
        this.setState({listtypes: ['string','checkbox','textarea','tag','multivalue-string']})
        this.setState({isListType: true})
        }
      else {
        this.setState({isListType: false})
      if (event.target.value === 'string') {
        this.setState({listtypes: ['list','checkbox','textarea','tag','multivalue-string']})
      }
      if (event.target.value === 'multivalue-string') {
        this.setState({listtypes: ['list','checkbox','textarea','tag','string']})
      }
      if (event.target.value === 'checkbox') {
        this.setState({listtypes: ['string','list','textarea','tag','multivalue-string']})
      }
      if (event.target.value === 'textarea') {
        this.setState({listtypes: ['string','list','checkbox','tag','multivalue-string']})
      }
      if (event.target.value === 'tag') {
        this.setState({listtypes: ['string','list','checkbox','textarea','multivalue-string']})
      }
    }

    this.setState({
      PendingChangeAppAttr: newAttr,
      AppAttributeData: newAttr
    })
    }
    if (type === 'listvalue') {
      let newAttr = Object.assign({}, this.state.AppAttributeData);
      newAttr.listvalue = event.target.value;
    this.setState({
      PendingChangeAppAttr: newAttr,
      AppAttributeData: newAttr
    })
    }
  }

  if (this.state.type === 'server'){
    if (type === 'name') {
      let newAttr = Object.assign({}, this.state.ServerAttributeData);
      newAttr.name = event.target.value.trim();
    this.setState({
      PendingChangeServerAttr: newAttr,
      ServerAttributeData: newAttr
    })
    }
    if (type === 'description') {
      let newAttr = Object.assign({}, this.state.ServerAttributeData);
      newAttr.description = event.target.value.trim();
    this.setState({
      PendingChangeServerAttr: newAttr,
      ServerAttributeData: newAttr
    })
    }
    if (type === 'type') {
      let newAttr = Object.assign({}, this.state.ServerAttributeData);
      newAttr.type = event.target.value;
      if (event.target.value === 'list') {
        this.setState({listtypes: ['string','checkbox','textarea','tag','multivalue-string']})
        this.setState({isListType: true})
        }
      else {
        this.setState({isListType: false})
      if (event.target.value === 'string') {
        this.setState({listtypes: ['list','checkbox','textarea','tag','multivalue-string']})
      }
      if (event.target.value === 'multivalue-string') {
        this.setState({listtypes: ['list','checkbox','textarea','tag','string']})
      }
      if (event.target.value === 'checkbox') {
        this.setState({listtypes: ['string','list','textarea','tag','multivalue-string']})
      }
      if (event.target.value === 'textarea') {
        this.setState({listtypes: ['string','list','checkbox','tag','multivalue-string']})
      }
      if (event.target.value === 'tag') {
        this.setState({listtypes: ['string','list','checkbox','textarea','multivalue-string']})
      }
    }

    this.setState({
      PendingChangeServerAttr: newAttr,
      ServerAttributeData: newAttr
    })
    }
    if (type === 'listvalue') {
      let newAttr = Object.assign({}, this.state.ServerAttributeData);
      newAttr.listvalue = event.target.value;
    this.setState({
      PendingChangeServerAttr: newAttr,
      ServerAttributeData: newAttr
    })
    }
}
  }

  onClickSaveAttr = event => {
    event.preventDefault();
    if (this.state.type === 'app') {
      if (this.state.selectedAppAttribute === ''){
        this.createAttr();
      } else {
        this.updateAttr();
      }
    }
    if (this.state.type === 'server') {
      if (this.state.selectedServerAttribute === ''){
        this.createAttr();
      } else {
        this.updateAttr();
      }
    }
  }

  onClickDeleteAttr = event => {
    event.preventDefault();
    this.deleteAttr();
  }

  render() {
    var isApp
    if (this.state.type === 'app'){
      isApp = true;
    }
    if (this.state.type === 'server'){
      isApp = false;
    }

    var isWaveId
    if (this.state.AppAttributeData.name && this.state.AppAttributeData.name.toLowerCase() === 'wave_id'){
      isWaveId = true;
    }
    else {
      isWaveId = false;
    }

    var AttrLoaded = false;
    if ((Object.keys(this.state.AppAttributeData).length > 0) && (this.state.type === 'app')){
      AttrLoaded = true;
    }
    if ((Object.keys(this.state.ServerAttributeData).length > 0) && (this.state.type === 'server')){
      AttrLoaded = true;
    }

    return (
      <div>
        {this.state.isLoading?<div className="block-events" ></div>:null}
    <div className="pt-3">
      <h4>{isApp?this.state.AppAttributeData.name:this.state.ServerAttributeData.name}</h4>
    </div>
    <div id="factory-tab" className="container-fluid rounded  py-3 px-0">
      <ul className="nav nav-tabs">
        <li className="nav-item">
          <span className="nav-link active">{this.state.type} Attribute Details {this.state.isLoading?<i className="fa fa-spinner fa-spin"></i>:null}</span>
        </li>
      </ul>
      <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">
        <div className="row px-3 pt-3"> <h3>{isApp?this.state.AppAttributeData.name:this.state.ServerAttributeData.name} &gt; Attribute Details</h3></div>
        <form>
          <div className="row px-3 pt-3">
            <div className="col-6 px-0 pr-5">
                <div className="form-group">
                  <label htmlFor="appName">Name:</label>
                  <input disabled={!AttrLoaded}
                         className="form-control form-control-sm"
                         key={isApp?this.state.AppAttributeData.type:this.state.ServerAttributeData.type}
                         onChange={this.onChangeAttrName('name')}
                         value={isApp?this.state.AppAttributeData.name:this.state.ServerAttributeData.name}
                         type="text"/>
                </div>
                <div className="form-group">
                  <label htmlFor="appDescription">Description:</label>
                  <input disabled={!AttrLoaded}
                         className="form-control form-control-sm"
                         key={isApp?this.state.AppAttributeData.name:this.state.ServerAttributeData.name}
                         onChange={this.onChangeAttrName('description')}
                         value={isApp?this.state.AppAttributeData.description:this.state.ServerAttributeData.description}
                         type="text"/>
                </div>

                <div className="form-group">
                  <label htmlFor="appType">Type:</label>
                  <select disabled={!AttrLoaded} onChange={this.onChangeAttrName('type')} className="form-control form-control-sm" id="attType">
                    <option > {isApp?this.state.AppAttributeData.type:this.state.ServerAttributeData.type} </option>
                    {isWaveId?'string':this.state.listtypes.map((item, index) => {
                      return (
                        <option key={item} value={item}>{item}</option>
                      )
                    })}
                  </select>
                  </div>
                  { this.state.isListType &&
                      <div className="form-group">
                        <label htmlFor="listValue">List Value:</label>
                        <input disabled={!AttrLoaded}
                        className="form-control form-control-sm"
                        key={isApp?this.state.AppAttributeData.name:this.state.ServerAttributeData.name}
                        onChange={this.onChangeAttrName('listvalue')}
                        value={isApp?this.state.AppAttributeData.listvalue:this.state.ServerAttributeData.listvalue}
                        type="text"/>
                      </div>
                  }
                <input disabled={!AttrLoaded}
                       className="btn btn-primary btn-outline mt-3 mr-3"
                       value="Save Attribute"
                       onClick={this.onClickSaveAttr}
                       type="button"/>
                <input disabled={!AttrLoaded}
                       className="btn btn-danger btn-outline mt-3"
                       value="Delete Attribute"
                       onClick={this.onClickDeleteAttr}
                       type="button"/>
            </div>
          </div>
        </form>
        </div>
      </div>
      </div>
    );
  }
};
