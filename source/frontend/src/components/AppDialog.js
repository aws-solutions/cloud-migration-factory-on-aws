import React, { Component } from "react";

export default class AdminAttributeDialog extends Component {
  constructor(props) {
    super(props);

    this.state = {
      showDialog: this.props.showDialog,
      msg: this.props.msg
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog
    });
    this.setState({
      msg: nextProps.msg
    });
  }

  onClickCancelDialog = event => {
    this.setState({
      showDialog: false
    });
    this.props.onClickUpdate()
  }

  render() {
    let styles = this.state.showDialog
      ? { display: "block" }
      : { display: "none" };
    return (
      <div>

        {this.state.showDialog &&
          <div>
            <div className="block-events"> </div>
            <div class="modal fade show" data-backdrop="static" style={styles} id="ModalCenter" tabindex="-1" role="dialog" aria-labelledby="ModalCenterTitle" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="ModalLongTitle">
                <div className="pb-4">
                        <b>Access is denied</b>
                      </div>
                </h5>
              </div>
              <div class="modal-body">
                <div style={{height:"170px",overflow:"auto"}}>
                    {this.state.msg}
                </div>
              </div>
              <div class="modal-footer">
                        <span onClick={this.onClickCancelDialog} className="onhover float-right"><button type="button" class="btn btn-primary" data-dismiss="modal">Close</button></span>
              </div>
            </div>
          </div>
        </div>
          </div>
        }

    </div>
    )
  }
}
