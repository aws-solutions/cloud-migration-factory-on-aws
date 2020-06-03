import React, { Component } from "react";
import { Auth} from "aws-amplify";
import AdminNav from "../components/AdminNav";
import AdminAttributeList from "../components/AdminAttributeList";
import AdminAttributeTab from "../components/AdminAttributeTab";
import AdminStageList from "../components/AdminStageList";
import AdminStageTab from "../components/AdminStageTab";
import Admin from "../actions/admin";
import NavBar from "../components/NavBar";
import AppDialog from "../components/AppDialog";

export default class AdminAttribute extends Component {
  constructor(props) {
    super(props);
    this.state = {
      stage: '',
      isAuthenticated: props.isAuthenticated,
      activeNav: 'attribute',
      isLoading: true,
      appAttributes: {attributes:[]},
      serverAttributes: {attributes:[]},
      selectedAppAttribute: '',
      selectedServerAttribute: '',
      AppAttributeData: {},
      ServerAttributeData: {},
      listtypes: [],
      isListType: false,
      type: '',
      jwt: {},
      allowedCreate: false,
      showDialog: false,
      msg: ''
    };
  }

  decodeJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace('-', '+').replace('_', '/');
    const decodedJwt = JSON.parse(window.atob(base64));
    this.setState({jwt: decodedJwt});
  }

  async componentDidMount() {
    try {
      const session = await Auth.currentSession();
      const token = session.idToken.jwtToken;
      this.api = await new Admin(session);
      this.getAppAttributes();
      this.getServerAttributes()
      this.decodeJwt(token);
      this.getPermissions();

    } catch (e) {
      console.log(e);
    }

    this.setState({ isLoading: false });
  }

  async getPermissions() {
    try {
        const userGroups = this.state.jwt['cognito:groups'];
        if (!(userGroups.includes('admin'))) {
          this.setState({
            showDialog: true,
            msg: "You are not authorized to manage the admin page"
          });
        }
        else {
          this.setState({
            allowedCreate: true
          });
          }
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
  }

  onClickUpdate = event => {
    this.setState({
      showDialog: false
    });
    this.props.history.push("/");
  }

  onLoadMenu = async event => {
    const session = await Auth.currentSession();
    const token = session.idToken.jwtToken;
    this.apiAdmin = await new Admin(session);
    this.decodeJwt(token);
    this.getPermissions();
  }

  onClickCreateNew = type => async event => {
    event.preventDefault();
    const newAttr = {
      name: ''
    };
    this.setState({listtypes: ['string','multivalue-string','list','checkbox','textarea','tag']})
    if (type === 'app') {
    this.setState({
      AppAttributeData: newAttr,
      selectedAppAttribute: '',
      type: 'app'
    });
  }
  if (type === 'server') {
    this.setState({
      ServerAttributeData: newAttr,
      selectedServerAttribute: '',
      type: 'server'
    });
  }
  }

  setselectedAttribute = (name,type) => async event => {
    event.preventDefault();
    this.setState({ isLoading: true });
    try {
      var lt = ['string','multivalue-string','list','checkbox','textarea','tag']
      if (type === 'app') {
      for (var x of this.state.appAttributes.attributes) {
        if (x.name === name) {
          var index = lt.indexOf(x.type)
          if (index > -1) {
            lt.splice(index, 1);
         }
         if (x.type === 'list') {
         this.setState({isListType: true})
         }
         else {
          this.setState({isListType: false})
         }
          this.setState({
            selectedAppAttribute: name,
            AppAttributeData: x,
            type: type,
            listtypes: lt
          })
        }
      }
    }
    if (type === 'server') {
      for (x of this.state.serverAttributes.attributes) {
        if (x.name === name) {
          index = lt.indexOf(x.type)
          if (index > -1) {
            lt.splice(index, 1);
         }
         if (x.type === 'list') {
          this.setState({isListType: true})
          }
          else {
           this.setState({isListType: false})
          }
          this.setState({
            selectedServerAttribute: name,
            ServerAttributeData: x,
            type: type,
            listtypes: lt
          })
        }
      }
    }

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({ isLoading: false });
  }

  updateAttrList = (action, attr, type) => {
    var i = 0;
    this.setState({
      selectedAppAttribute: ''
    });
    switch(action) {
      case 'update':
        if (type === 'app') {
          this.getAppAttributes();
          if (attr.type === 'list') {
            this.setState({isListType: true})
          }
          else {
            this.setState({isListType: false})
          }
          this.setState({
            selectedAppAttribute: attr.name,
            AppAttributeData: attr,
          });
        }
        if (type === 'server') {
          this.getServerAttributes();
          if (attr.type === 'list') {
            this.setState({isListType: true})
          }
          else {
            this.setState({isListType: false})
          }
          this.setState({
            selectedServerAttribute: attr.name,
            ServerAttributeData: attr,
          });
        }

        break;

      case 'add':

        if (type === 'app') {
          this.getAppAttributes();
          if (attr.type === 'list') {
            this.setState({isListType: true})
          }
          else {
            this.setState({isListType: false})
          }
          this.setState({
            selectedAppAttribute: attr.name,
            AppAttributeData: attr,
          });
        }
        if (type === 'server') {
          this.getServerAttributes();
          if (attr.type === 'list') {
            this.setState({isListType: true})
          }
          else {
            this.setState({isListType: false})
          }
          this.setState({
            selectedServerAttribute: attr.name,
            ServerAttributeData: attr,
          });
        }
        break;

      case 'delete':
          if (type === 'app') {
            this.setState({
              selectedAppAttribute: ''
            });
          for ( i = 0; i < this.state.appAttributes.attributes.length; i++) {
            if (attr === this.state.appAttributes.attributes[i].name) {
              let newAttrs = Array.from(this.state.appAttributes.attributes);
              newAttrs.splice(i, 1);
              this.setState({
                appAttributes: {attributes: newAttrs},
                selectedAppAttribute: '',
                AppAttributeData: {},
              });
            }
          }
        }
        if (type === 'server') {
          this.setState({
            selectedServerAttribute: ''
          });
          for ( i = 0; i < this.state.serverAttributes.attributes.length; i++) {
            if (attr === this.state.serverAttributes.attributes[i].name) {
              let newAttrs = Array.from(this.state.serverAttributes.attributes);
              newAttrs.splice(i, 1);
              this.setState({
                serverAttributes: {attributes: newAttrs},
                selectedServerAttribute: '',
                ServerAttributeData: {}
              });
            }
          }
        }

        break;

      default:
        break;
    }
  }

  changeActiveNav(event) {
    switch(event.target.id) {
      case 'stage':
        this.props.history.push("/admin/stage");
        break;
      case 'role':
        this.props.history.push("/admin/role");
        break;
      default:
        break;
    }
  }

  async getAppAttributes(session) {
    const response = await this.api.getAppAttributes();
    this.setState({ appAttributes: response});

  }catch (e) {
    console.log(e);
    if ('data' in e.response) {
      this.props.showError(e.response.data);
    }
  }

  async getServerAttributes(session) {
    try{
      const response = await this.api.getServerAttributes();
      this.setState({ serverAttributes : response});
    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  listView() {
    switch(this.state.activeNav) {
      case 'attribute':
        return <AdminAttributeList
        selectedAppAttribute={this.state.selectedAppAttribute}
        selectedServerAttribute={this.state.selectedServerAttribute}
        onClick={this.setselectedAttribute}
        appAttributes={this.state.appAttributes}
        serverAttributes={this.state.serverAttributes}
        isLoading={this.state.isLoading}
        onClickCreateNew={this.onClickCreateNew}
        type={this.state.type}
        />;
      case 'stage':
        return <AdminStageList
          selectedAttribute={this.state.selectedAttribute}
          onClick={this.setselectedAttribute.bind(this)}
          stages={this.state.stages}
        />;
      case 'role':
        return <AdminAttributeList />;
      default:
        return <AdminAttributeList />;
    }
  }

  tabView() {
    switch(this.state.activeNav) {
      case 'attribute':
        return <AdminAttributeTab
        AppAttributeData={this.state.AppAttributeData}
        ServerAttributeData={this.state.ServerAttributeData}
        selectedAppAttribute={this.state.selectedAppAttribute}
        selectedServerAttribute={this.state.selectedServerAttribute}
        updateAttrList={this.updateAttrList}
        isLoading={this.state.isLoading}
        type={this.state.type}
        showError={this.props.showError}
        listtypes={this.state.listtypes}
        isListType={this.state.isListType}
        />;
      case 'stage':
        return <AdminStageTab
          stage={this.state.data}
        />;
      case 'role':
        return <AdminAttributeList />;
      default:
        return <AdminAttributeList />;
    }
  }


  render() {
    if (!this.state.isAuthenticated){
      this.props.history.push("/login");
    }

    if (!this.state.allowedCreate) {
      return (
        <div>
        <AppDialog
        showDialog={this.state.showDialog}
        msg={this.state.msg}
        onClickUpdate={this.onClickUpdate}
      />
      </div>
      )
    }

    else {
    return (
      <div>
        <NavBar
          onClick={this.props.onClickMenu}
          onLoad={this.props.onLoadMenu}
          selection="Admin"
        />
        <AdminNav onClick={this.changeActiveNav.bind(this)} active={this.state.activeNav}/>
        <div className="container-fluid">
          <div className="row">
            <div className="col-3">
            {this.listView()}
            </div>
            <div className="col-9">
              {this.tabView()}
            </div>
          </div>
        </div>
      </div>
    );
    }
  }
}
