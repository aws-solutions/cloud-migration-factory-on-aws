import React from "react";

export default class AdminNav extends React.Component {
  render() {
    return (
      <div className="row px-5 my-0 py-1 aws-dark">
        <div className="col-2">
            <div id="attribute" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='attribute'?'text-warning':'text-muted')}>
              Attribute Configuration
            </div>
        </div>
        <div className="col-2">
            <div id="stage" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='stage'?'text-warning':'text-muted')}>
              Stage Configuration
            </div>
        </div>
        <div className="col-2">
            <div id="role" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='role'?'text-warning':'text-muted')}>
              Role Configuration
            </div>
        </div>
      </div>
    );
  }
};
