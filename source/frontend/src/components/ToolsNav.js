import React from "react";

export default class ToolsNav extends React.Component {
  render() {
    return (
      <div className="row px-5 my-0 py-1 aws-dark">
        <div className="col-2">
            <div id="ce" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='ce'?'text-warning':'text-muted')}>
              CloudEndure
            </div>
        </div>
        <div className="col-2">
            <div id="ams" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='ams'?'text-warning':'text-muted')}>
              AWS Managed Services
            </div>
        </div>
      </div>
    );
  }
};
