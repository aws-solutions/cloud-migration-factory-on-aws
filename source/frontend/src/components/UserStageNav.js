import React from "react";

export default class UserStageNav extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stages: props.stages,
      isLoading: props.isLoading,
      selectedStage: props.selectedStage,
      minView: 0,
      maxView: 5,
    };
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.selectedStage !== this.props.selectedStage || nextProps.stages !== this.props.stages){

      // Shift nav view if selection is not in viewing area
      if (nextProps.selectedStage != null && nextProps.stages.length > 6 && nextProps.selectedStage > this.state.maxView){
        this.setState({
          minView: nextProps.selectedStage - 5,
          maxView: nextProps.selectedStage
        });
      }

      this.setState({
        stages: nextProps.stages,
        isLoading: nextProps.isLoading,
        selectedStage: nextProps.selectedStage
      });
    };
  }

  shiftNavLeft = event => {
    event.preventDefault();
    event.stopPropagation();

    const newMinView = this.state.minView - 1;
    const newMaxView = this.state.maxView - 1;

    this.setState({
      minView: newMinView,
      maxView: newMaxView
    })

  }

  shiftNavRight = event => {
    event.preventDefault();
    event.stopPropagation();

    const newMinView = this.state.minView + 1;
    const newMaxView = this.state.maxView + 1;

    this.setState({
      minView: newMinView,
      maxView: newMaxView
    })

  }

  render() {

    const selected = this.state.selectedStage;
    var colWidth = 2;
    if (this.state.stages.length < 6){
      colWidth = Math.floor(12/this.state.stages.length);
    }

    return (
      <div className="row bs-wizard py-0 my-0 py-1 aws-dark border-bottom-0">
        {this.state.stages.map((item, index) => {

          var status = 'disabled';
          if (index===selected){
            status = 'active';
          } else if (index<selected){
            status = 'complete';
          }

          const minView = this.state.minView;
          const maxView = this.state.maxView;

          if (index < minView || index > maxView) {
            return null
          }

          return (
            <div key={item.stage_id} onClick={this.props.onClick(index)} className={'col-'+colWidth+' bs-wizard-step '+status} data-bs-wizard-step={index}>
                {(index === minView && minView > 0)&&
                  <div onClick={this.shiftNavLeft} className="text-warning stage-nav stage-nav-left">{'<'}</div>
                }
                {(index === maxView && maxView < this.state.stages.length-1)&&
                  <div onClick={this.shiftNavRight} className="text-warning stage-nav stage-nav-right">{'>'}</div>
                }

                <div className={'text-center bs-wizard-stepnum '+(status==='active'?'text-warning':'')}>{item.stage_name}</div>
                <div className="progress"><div className="progress-bar"></div></div>
                <span className="bs-wizard-dot"></span>
            </div>
          )
        })}

      </div>
    );
  }
};
