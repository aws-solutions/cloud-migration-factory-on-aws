import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";

export default class UserListWaves extends Component {
  constructor(props) {
    super(props);

    this.state = {
      waves: props.waves,
      isLoading: props.isLoading,
      isLocked: false
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiUser = await new User(session);
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading,
      waves: nextProps.waves,
    });
  }

  async deleteWave(wave_id) {
    this.setState({isLocked: true});

    try {
      await this.apiUser.deleteWave(wave_id);
      this.props.updateWaveList('delete', wave_id)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  async createWave(wave_name) {
    this.setState({isLocked: true});

    var wave ={wave_name: wave_name}

    try {
      await this.apiUser.postWave(wave);
      this.props.updateWaveList('refresh', wave_name)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  onClickRemoveWave = wave_id => event => {
    event.preventDefault();
    if (this.state.isLocked !== true){
      this.deleteWave(wave_id);
    }
  }

  onClickCreateWave = event => {
    event.preventDefault();
    if (this.state.isLocked !== true && this.newWaveName.value.length > 0){
      this.createWave(this.newWaveName.value);
      this.newWaveName.value = '';
    }
  }

  onKeyUpNewWave = event => {
    if(event.key==='Enter' && this.state.isLocked !== true && this.newWaveName.value.length > 0){
      this.createWave(event.target.value);
      event.target.value ='';
    }
  }

  render() {

    return (
      <div className="container-fluid rounded">


        <div>
          <table className={"table " + (this.state.isLoading?null:'table-hover')}>
            <thead className="thead-dark">
              <tr>
                <th scope="col">wave_name</th>
                <th scope="col">wave_id</th>
                <th scope="col">action</th>
              </tr>
            </thead>
            <tbody>
              {this.state.isLoading?
                <tr><td><i className="fa fa-spinner fa-spin"></i> Loading Waves...</td></tr>
                :
                <tr>
                  <td key='input'>
                    <input
                      ref={(newWaveName) => { this.newWaveName = newWaveName }}
                      disabled={this.state.isLocked}
                      type="text"
                      className="form-control form-control-sm"
                      onKeyUp={this.onKeyUpNewWave}
                      placeholder='Create new wave'
                    />
                  </td>
                  <td></td>
                  <td><a href="." onClick={this.onClickCreateWave} className="pr-3">Add Wave</a></td>
                </tr>
              }

              {this.state.waves.map((item, index) => {
                return (
                  <tr key={index}>
                    <td>{item.wave_name}</td>
                    <td>{item.wave_id}</td>
                    <td><a href="." disabled={this.state.isLocked} onClick={this.onClickRemoveWave(item.wave_id)} className="pr-3 text-danger">Delete</a></td>
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
