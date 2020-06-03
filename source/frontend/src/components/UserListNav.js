import React from "react";

export default class UserListNav extends React.Component {
  render() {
    return (
      <div className="row px-5 my-0 py-1 aws-dark">
        <div className="col-2">
            <div id="apps" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='apps'?'text-warning':'text-muted')}>
              Application List
            </div>
        </div>
        <div className="col-2">
            <div id="servers" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='servers'?'text-warning':'text-muted')}>
              Server List
            </div>
        </div>
        <div className="col-2">
            <div id="waves" onClick={this.props.onClick} className={"text-center btn "+(this.props.active==='waves'?'text-warning':'text-muted')}>
              Wave List
            </div>
        </div>
      </div>
    );
  }
};
