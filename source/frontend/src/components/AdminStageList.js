import React from "react";

export default class AdminStageList extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stages: props.stages,
      isLoading: props.isLoading,
      selectedStage: ''
    };
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.stages !== this.props.stages){
      this.setState({
        stages: nextProps.stages,
        isLoading: nextProps.isLoading,
        selectedStage: nextProps.selectedStage
      });
    };
  }

  render() {

    return (
      <div className="container-fluid rounded service-list">
        <div className="pb-2 pt-3">
          <a href="." onClick={this.props.onClickCreateNew}>+ Create new stage</a>
        </div>
        <div className="tableFixHead">
          <table className={"table " + (this.state.isLoading?null:'table-hover')}>
            <tbody>
              {this.state.isLoading?<tr><td><i className="fa fa-spinner fa-spin"></i> Loading Stages...</td></tr>:null}
              {this.state.stages.map((item, index) => {
                var style = ''
                if (item.stage_id === this.props.selectedStage){
                  style = 'bg-grey'
                }
                return (
                  <tr key={item.stage_id} className={style} onClick={this.props.onClick(item.stage_id)}>
                    <td>{item.stage_id+' - '+item.stage_name}</td>
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
