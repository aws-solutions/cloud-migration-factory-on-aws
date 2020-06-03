import React from "react";

export default class UserAppList extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      apps: props.apps,
      waves: props.waves,
      filteredApps: props.apps,
      isLoading: props.isLoading,
      selectedApp: '',
      searchWave: 'All',
      searchApp: '',
      allowCreate: props.allowCreate
    };
  }

  componentWillReceiveProps(nextProps){
    // Prevent state change unless app selection changed
    if (nextProps.apps !== this.props.apps){
      this.setState({
        apps: nextProps.apps,
        filteredApps: nextProps.apps,
        isLoading: nextProps.isLoading,
        selectedApp: nextProps.selectedApp
      });
    };

    this.setState({
      allowCreate: nextProps.allowCreate
    });

    if (nextProps.waves !== this.props.waves){
      this.setState({
        waves: nextProps.waves,
      });
    };
  }

  componentDidUpdate() {

  }

  filterAppList () {
    var newAppList = [];

    for (var app in this.state.apps){
      if (this.state.apps[app].wave_id === this.state.searchWave || this.state.searchWave === 'All'){
        if (this.state.searchApp === '' || this.state.apps[app].app_name.includes(this.state.searchApp)){
          newAppList.push(this.state.apps[app]);
        }
      }
      else {
        if ((this.state.apps[app].wave_id ==='' || !('wave_id' in this.state.apps[app])) && this.state.searchWave === 'Not Assigned') {
          if (this.state.searchApp === '' || this.state.apps[app].app_name.includes(this.state.searchApp)){
            newAppList.push(this.state.apps[app]);
          }
        }
      }
    }
    this.setState({filteredApps: newAppList});
  }

  onChangeWave  = event => {
    this.setState({searchWave: event.target.value}, this.filterAppList);
  }

  onChangeSearch  = event => {
    this.setState({searchApp: event.target.value}, this.filterAppList);
  }

  render() {

    return (
      <div className="container-fluid rounded service-list">

        <div className="form-group pt-3">
          <label htmlFor="waveId">Application Filter:</label>
          <select onChange={this.onChangeWave} className="form-control form-control-sm" defaultValue="none" id="waveId">
            <option value="none" disabled>Filter on migration wave</option>
            <option value="All">All</option>
            <option value="Not Assigned">Not Assigned</option>
            {this.state.waves.map((item, index) => {
              return (
                <option key={item.wave_id} value={item.wave_id}>{item.wave_name}</option>
              )
            })}

          </select>
        </div>

        <div className="form-group">
          <input
            type="text"
            className="form-control form-control-sm"
            onChange={this.onChangeSearch}
            placeholder='Search by app name'
          />
        </div>

        {this.state.allowCreate &&
          <div className="pb-3">
            <a href="." onClick={this.props.onClickCreateNew}>+ Create new application</a>
          </div>
        }

        <div className="tableFixHead">
          <table className={"table " + (this.state.isLoading?null:'table-hover')}>
            <tbody>
              {this.state.isLoading?<tr><td><i className="fa fa-spinner fa-spin"></i> Loading Applications...</td></tr>:null}
              {this.state.filteredApps.map((item, index) => {
                var style = ''
                if (item.app_id === this.props.selectedApp){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.app_id} className={style} onClick={this.props.onClick(item.app_id)}>
                    <td>{item.app_name}</td>
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
