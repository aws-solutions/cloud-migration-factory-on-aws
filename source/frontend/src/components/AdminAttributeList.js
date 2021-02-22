import React from "react";

export default class AdminAttributeList extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      isLoading: props.isLoading,
      waveAttributes: props.waveAttributes,
      appAttributes: props.appAttributes,
      serverAttributes: props.serverAttributes,
      selectedWaveAttribute: '',
      selectedAppAttribute: '',
      selectedServerAttribute: '',
      type: 'wave',
    };
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.waveAttributes !== this.props.waveAttributes){
      this.setState({
        waveAttributes: nextProps.waveAttributes,
        selectedWaveAttribute: nextProps.selectedWaveAttribute,
        isLoading: nextProps.isLoading
      });
    }
    if (nextProps.appAttributes !== this.props.appAttributes){
      this.setState({
        appAttributes: nextProps.appAttributes,
        selectedAppAttribute: nextProps.selectedAppAttribute,
        isLoading: nextProps.isLoading
      });
    }
    if (nextProps.serverAttributes !== this.props.serverAttributes){
      this.setState({
        serverAttributes: nextProps.serverAttributes,
        selectedServerAttribute: nextProps.selectedServerAttribute,
        isLoading: nextProps.isLoading
      });
    };
    if (nextProps.type !== this.props.type){
      this.setState({
        type: nextProps.type
      });
    };
    this.setState({ isLoading: nextProps.isLoading });
  }

  onSelectAttrType = (type) => (event) => {
    if (event.target.value === 'Wave Attributes') {
      this.setState({type: 'wave'})
      }
    if (event.target.value === 'Application Attributes') {
    this.setState({type: 'app'})
    }
    if (event.target.value === 'Server Attributes') {
      this.setState({type: 'server'})
      }
  }

  render() {
    return (
  <div className="container-fluid rounded service-list">
    <div className="form-group pt-3">
      <label htmlFor="attType">Select Attribute Type:</label>
      <select ref="serverAttributes" onChange={this.onSelectAttrType()} className="form-control form-control-sm" id="attType">
        <option>Wave Attributes</option>
        <option>Application Attributes</option>
        <option>Server Attributes</option>
      </select>
    </div>
    <div className="pb-2">
      <a href="." onClick={this.props.onClickCreateNew(this.state.type)}>+ Create new schema attribute</a>
    </div>
    <div className="tableFixHead">
      <table className={"table " + (this.state.isLoading?null:'table-hover')}>
        <tbody>
          {this.state.isLoading?<tr><td><i className="fa fa-spinner fa-spin"></i> Loading Attributes...</td></tr>:null}

          {(this.state.waveAttributes.attributes && this.state.waveAttributes.attributes.length > 0) &&
            this.state.waveAttributes.attributes.map((item, index) => {
              if (this.state.type === 'wave') {
                var style = ''
                if (item.name === this.props.selectedWaveAttribute){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.name} className={style} onClick={this.props.onClick(item.name, 'wave')}>
                    <td>{item.name}</td>
                  </tr>
                )
              }
              return null;
            })}

          {(this.state.appAttributes.attributes && this.state.appAttributes.attributes.length > 0) &&
            this.state.appAttributes.attributes.map((item, index) => {
              if (this.state.type === 'app') {
                var style = ''
                if (item.name === this.props.selectedAppAttribute){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.name} className={style} onClick={this.props.onClick(item.name, 'app')}>
                    <td>{item.name}</td>
                  </tr>
                )
              }
              return null;
            })}

          {(this.state.serverAttributes.attributes && this.state.serverAttributes.attributes.length > 0)&&
            this.state.serverAttributes.attributes.map((item, index) => {
              if (this.state.type === 'server') {
                var style = ''
                if (item.name === this.props.selectedServerAttribute){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.name} className={style} onClick={this.props.onClick(item.name, 'server')}>
                    <td>{item.name}</td>
                  </tr>
                )
              }
              return null;
          })}

        </tbody>
      </table>
    </div>
  </div>
    );
  }
};
